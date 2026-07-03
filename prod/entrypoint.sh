#!/bin/bash
set -e

# =============================================================================
# Mapeo de variables de entorno a las que Odoo espera
# Usamos nombres únicos (DB_HOST, DB_USER, etc.) para evitar conflictos
# con variables del sistema como HOST/USER
# =============================================================================

if [ -n "$DB_HOST" ]; then
    export HOST="$DB_HOST"
fi

if [ -n "$DB_USER" ]; then
    export USER="$DB_USER"
fi

if [ -n "$DB_PASSWORD" ]; then
    export PASSWORD="$DB_PASSWORD"
fi

if [ -n "$DB_NAME" ]; then
    export DB="$DB_NAME"
fi

if [ -n "$DB_PORT" ]; then
    export PORT="$DB_PORT"
fi

# Ejecutar el entrypoint original de Odoo
exec /entrypoint.sh "$@"
