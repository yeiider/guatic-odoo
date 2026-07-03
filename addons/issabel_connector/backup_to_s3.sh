#!/bin/bash

################################################################################
# Script: Monitor en Tiempo Real de Grabaciones Issabel
# Descripción: Detecta nuevas grabaciones, las sube a S3 y las elimina localmente
# Usa: inotify para monitoreo de filesystem en tiempo real
################################################################################

set -euo pipefail
IFS=$'\n\t'

################################################################################
# CONFIGURACIÓN
################################################################################

RECORDINGS_DIR="/var/spool/asterisk/monitor"
LOG_FILE="/var/log/issabel_backup/realtime_backup.log"
PID_FILE="/var/run/issabel_watcher.pid"

# AWS Configuration
S3_BUCKET="odoo-issabel-record"
S3_PREFIX="recordings"  # Solo "recordings" para estructura plana
AWS_PROFILE="default"
AWS_REGION="us-east-1"

# Configuración de procesamiento
UPLOAD_DELAY=30  # Segundos de espera después de creación (para asegurar que el archivo está completo)
DELETE_AFTER_UPLOAD=true  # Eliminar archivo local después de subir exitosamente

################################################################################
# FUNCIONES
################################################################################

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_dependencies() {
    local deps=("inotifywait" "aws")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log "ERROR: Comando requerido no encontrado: $cmd"
            if [ "$cmd" = "inotifywait" ]; then
                log "INFO: Instalar con: yum install inotify-tools"
            fi
            exit 1
        fi
    done
}

check_pid() {
    if [ -f "$PID_FILE" ]; then
        local old_pid=$(cat "$PID_FILE")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            log "ERROR: El script ya está ejecutándose con PID $old_pid"
            exit 1
        else
            log "INFO: Eliminando PID file obsoleto"
            rm -f "$PID_FILE"
        fi
    fi
}

create_pid() {
    echo $$ > "$PID_FILE"
    trap 'rm -f "$PID_FILE"; log "INFO: Monitor detenido"; exit' EXIT INT TERM
}

upload_to_s3() {
    local file=$1
    local filename=$(basename "$file")
    
    # Subir con solo el nombre del archivo (sin ruta)
    local s3_key="${S3_PREFIX}/${filename}"
    
    log "INFO: Subiendo a S3: ${filename}"
    
    if aws s3 cp "$file" "s3://${S3_BUCKET}/${s3_key}" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --storage-class STANDARD_IA \
        --server-side-encryption AES256 \
        --metadata "upload-date=$(date -u +%Y-%m-%dT%H:%M:%SZ),source=issabel-realtime" \
        --no-progress 2>> "$LOG_FILE"; then
        
        local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        log "SUCCESS: Subido ${filename} - $(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo "${size} bytes")"
        return 0
    else
        log "ERROR: Fallo al subir: ${filename}"
        return 1
    fi
}

is_recording_file() {
    local file=$1
    local filename=$(basename "$file")
    
    # Verificar extensiones válidas
    if [[ "$filename" =~ \.(wav|WAV|mp3|MP3|gsm|GSM)$ ]]; then
        return 0
    fi
    return 1
}

wait_for_file_completion() {
    local file=$1
    local max_wait=300  # 5 minutos máximo
    local elapsed=0
    local last_size=0
    
    # Esperar el delay inicial
    sleep "$UPLOAD_DELAY"
    
    # Verificar que el archivo no esté creciendo
    while [ $elapsed -lt $max_wait ]; do
        if [ ! -f "$file" ]; then
            log "WARN: Archivo desapareció durante la espera: $(basename "$file")"
            return 1
        fi
        
        local current_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        if [ "$current_size" -eq "$last_size" ] && [ "$current_size" -gt 0 ]; then
            # El archivo no ha cambiado de tamaño, está completo
            log "INFO: Archivo completo y listo: $(basename "$file") (${current_size} bytes)"
            return 0
        fi
        
        last_size=$current_size
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    log "WARN: Timeout esperando completar archivo: $(basename "$file")"
    return 1
}

process_file() {
    local file=$1
    
    # Verificar que es un archivo de grabación válido
    if ! is_recording_file "$file"; then
        return 0
    fi
    
    log "INFO: Nueva grabación detectada: $(basename "$file")"
    
    # Esperar a que el archivo esté completo
    if ! wait_for_file_completion "$file"; then
        return 1
    fi
    
    # Subir a S3 (sin comprimir, directo)
    if upload_to_s3 "$file"; then
        # Eliminar archivo local si está configurado
        if [ "$DELETE_AFTER_UPLOAD" = true ]; then
            if rm -f "$file"; then
                log "INFO: Archivo local eliminado: $(basename "$file")"
            else
                log "WARN: No se pudo eliminar archivo local: $(basename "$file")"
            fi
        fi
        return 0
    else
        log "ERROR: No se eliminó el archivo local por fallo en upload: $(basename "$file")"
        return 1
    fi
}

# Procesar archivos en background para no bloquear el monitor
process_file_async() {
    local file=$1
    (
        process_file "$file"
    ) &
}

start_monitoring() {
    log "INFO: ====== Iniciando monitor en tiempo real ======"
    log "INFO: Monitoreando directorio: $RECORDINGS_DIR"
    log "INFO: Bucket S3: s3://${S3_BUCKET}/${S3_PREFIX}/"
    log "INFO: Eliminar después de subir: $([ "$DELETE_AFTER_UPLOAD" = true ] && echo "SÍ" || echo "NO")"
    log "INFO: Delay de upload: ${UPLOAD_DELAY}s"
    
    # Monitorear eventos: create, close_write, moved_to
    # close_write: Se dispara cuando un archivo se cierra después de ser escrito
    # moved_to: Se dispara cuando un archivo es movido al directorio
    inotifywait -m -r -e close_write -e moved_to --format '%w%f' "$RECORDINGS_DIR" |
    while read -r filepath; do
        # Procesar archivo de forma asíncrona
        process_file_async "$filepath"
    done
}

################################################################################
# MAIN
################################################################################

main() {
    # Crear directorio de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Verificar que no esté corriendo
    check_pid
    
    # Verificar dependencias
    check_dependencies
    
    # Verificar acceso a AWS
    if ! aws s3 ls "s3://${S3_BUCKET}" --profile "$AWS_PROFILE" --region "$AWS_REGION" &> /dev/null; then
        log "ERROR: No se puede acceder al bucket S3: ${S3_BUCKET}"
        exit 1
    fi
    
    # Verificar directorio de grabaciones
    if [ ! -d "$RECORDINGS_DIR" ]; then
        log "ERROR: Directorio de grabaciones no existe: $RECORDINGS_DIR"
        exit 1
    fi
    
    # Crear PID file
    create_pid
    
    # Iniciar monitoreo
    start_monitoring
}

# Ejecutar
main "$@"