#!/bin/bash
set -e

# =============================================================================
# Mapeo de variables de entorno a los argumentos de línea de comandos de Odoo
# Usamos CLI args en vez de exportar HOST/USER/PORT para evitar conflictos
# con variables del sistema que Coolify pueda interpretar mal
# =============================================================================

# Construir argumentos de base de datos para Odoo
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

# Los argumentos CLI sobreescriben el archivo odoo.conf
# Ejecutar el entrypoint original de Odoo con args adicionales
exec /entrypoint.sh $DB_ARGS "$@"
