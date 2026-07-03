#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

RECORDINGS_DIR="/var/spool/asterisk/monitor"
LOG_FILE="/var/log/issabel_backup/realtime_backup.log"
PID_FILE="/var/run/issabel_watcher.pid"
PROCESSING_LOCK_DIR="/var/run/issabel_watcher_locks"

S3_BUCKET="odoo-issabel-record"
S3_PREFIX="Grabaciones"
AWS_PROFILE="default"
AWS_REGION="us-east-1"

UPLOAD_DELAY=30
DELETE_AFTER_UPLOAD=true
MAX_RETRIES=3
RETRY_DELAY=10
MAX_CONCURRENT_UPLOADS=5

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_dependencies() {
    local deps=("inotifywait" "aws")
    local missing=()
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log "ERROR: Comandos requeridos no encontrados: ${missing[*]}"
        exit 1
    fi
}

check_pid() {
    if [ -f "$PID_FILE" ]; then
        local old_pid=$(cat "$PID_FILE")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            log "ERROR: El script ya está ejecutándose con PID $old_pid"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
}

create_pid() {
    echo $$ > "$PID_FILE"
    trap 'cleanup_exit' EXIT INT TERM
}

cleanup_exit() {
    rm -f "$PID_FILE"
    log "INFO: Monitor detenido"
    exit
}

get_file_size() {
    stat -c%s "$1" 2>/dev/null || echo "0"
}

format_size() {
    local bytes=$1
    local mb=$((bytes / 1048576))
    if [ $mb -gt 0 ]; then
        echo "${mb}MB"
    else
        echo "$((bytes / 1024))KB"
    fi
}

upload_to_s3() {
    local file=$1
    local filename=$(basename "$file")
    local s3_key="${S3_PREFIX}/${filename}"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        log "INFO: Subiendo a S3 (intento $attempt/$MAX_RETRIES): ${filename}"
        
        if aws s3 cp "$file" "s3://${S3_BUCKET}/${s3_key}" \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION" \
            --storage-class STANDARD_IA \
            --no-progress 2>> "$LOG_FILE"; then
            
            local size=$(get_file_size "$file")
            log "SUCCESS: Subido ${filename} - $(format_size $size)"
            return 0
        else
            log "WARN: Intento $attempt fallido para ${filename}"
            if [ $attempt -lt $MAX_RETRIES ]; then
                sleep $RETRY_DELAY
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    log "ERROR: Fallo al subir: ${filename}"
    return 1
}

is_recording_file() {
    local filename=$(basename "$1")
    [[ "$filename" =~ \.(wav|WAV|mp3|MP3|gsm|GSM)$ ]]
}

wait_for_file_completion() {
    local file=$1
    sleep "$UPLOAD_DELAY"
    
    local last_size=0
    local stable_count=0
    
    for i in {1..60}; do
        [ ! -f "$file" ] && return 1
        
        local current_size=$(get_file_size "$file")
        [ "$current_size" -eq 0 ] && return 1
        
        if [ "$current_size" -eq "$last_size" ]; then
            stable_count=$((stable_count + 1))
            [ $stable_count -ge 2 ] && return 0
        else
            stable_count=0
        fi
        
        last_size=$current_size
        sleep 5
    done
    
    return 1
}

get_lock_file() {
    echo "${PROCESSING_LOCK_DIR}/$(basename "$1").lock"
}

acquire_file_lock() {
    mkdir "$(get_lock_file "$1")" 2>/dev/null
}

release_file_lock() {
    rmdir "$(get_lock_file "$1")" 2>/dev/null || true
}

process_file() {
    local file=$1
    local filename=$(basename "$file")
    
    is_recording_file "$file" || return 0
    acquire_file_lock "$file" || return 0
    
    trap "release_file_lock '$file'" RETURN
    
    log "INFO: Nueva grabación detectada: ${filename}"
    
    [ ! -f "$file" ] && return 1
    wait_for_file_completion "$file" || return 1
    [ ! -f "$file" ] && return 1
    
    if upload_to_s3 "$file"; then
        if [ "$DELETE_AFTER_UPLOAD" = true ]; then
            rm -f "$file" && log "INFO: Archivo local eliminado: ${filename}"
        fi
        return 0
    else
        log "ERROR: Fallo en upload: ${filename}"
        return 1
    fi
}

process_file_async() {
    while [ $(jobs -r | wc -l) -ge $MAX_CONCURRENT_UPLOADS ]; do
        sleep 1
    done
    ( process_file "$1" ) &
}

process_existing_files() {
    log "INFO: Buscando archivos existentes..."
    local count=0
    
    while IFS= read -r -d '' file; do
        [ -f "$file" ] || continue
        count=$((count + 1))
        log "INFO: Archivo existente: $(basename "$file")"
        process_file_async "$file"
    done < <(find "$RECORDINGS_DIR" -type f \( -name "*.wav" -o -name "*.mp3" -o -name "*.gsm" \) -print0 2>/dev/null)
    
    log "INFO: Encontrados $count archivos existentes"
}

start_monitoring() {
    log "INFO: ====== Iniciando monitor ======"
    log "INFO: Directorio: $RECORDINGS_DIR"
    log "INFO: S3: s3://${S3_BUCKET}/${S3_PREFIX}/"
    log "INFO: Eliminar: $([ "$DELETE_AFTER_UPLOAD" = true ] && echo SI || echo NO)"
    
    process_existing_files
    log "INFO: Monitoreando archivos nuevos..."
    
    inotifywait -m -r -q -e close_write --format '%w%f' "$RECORDINGS_DIR" |
    while read -r filepath; do
        process_file_async "$filepath"
    done
}

main() {
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$PROCESSING_LOCK_DIR"
    
    check_pid
    check_dependencies
    
    log "INFO: Verificando S3..."
    if ! aws s3 ls "s3://${S3_BUCKET}" --profile "$AWS_PROFILE" --region "$AWS_REGION" &> /dev/null; then
        log "ERROR: No se puede acceder a S3: ${S3_BUCKET}"
        exit 1
    fi
    
    [ ! -d "$RECORDINGS_DIR" ] && log "ERROR: Directorio no existe" && exit 1
    
    create_pid
    start_monitoring
}

main "$@"
