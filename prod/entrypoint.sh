#!/bin/bash
set -e

# =============================================================================
# Mapeo de variables de entorno a los argumentos de línea de comandos de Odoo
# Usamos nombres únicos (DB_HOST, DB_USER, etc.) para evitar conflictos
# con variables del sistema como HOST/USER
# =============================================================================

# Construir argumentos de base de datos
DB_ARGS=""

if [ -n "$DB_HOST" ]; then
    DB_ARGS="$DB_ARGS --db_host=$DB_HOST"
fi

if [ -n "$DB_PORT" ]; then
    DB_ARGS="$DB_ARGS --db_port=$DB_PORT"
fi

if [ -n "$DB_USER" ]; then
    DB_ARGS="$DB_ARGS --db_user=$DB_USER"
fi

if [ -n "$DB_PASSWORD" ]; then
    DB_ARGS="$DB_ARGS --db_password=$DB_PASSWORD"
fi

if [ -n "$DB_NAME" ]; then
    DB_ARGS="$DB_ARGS --database=$DB_NAME"
fi

# Los argumentos de línea de comandos sobreescriben el archivo de configuración
# Esto es clave porque odoo.conf tiene valores hardcodeados
set -- "$@" $DB_ARGS

# Ejecutar el entrypoint original de Odoo con los argumentos adicionales
exec /entrypoint.sh "$@"
