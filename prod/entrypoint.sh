#!/bin/bash
set -e

# =============================================================================
# Mapeo DB_HOST/DB_USER/DB_PASSWORD/DB_PORT/DB_NAME → HOST/USER/PASSWORD/PORT/DB_NAME
# para que el entrypoint original de Odoo los use (vía : ${HOST:=...})
# =============================================================================

[ -n "$DB_HOST" ] && export HOST="$DB_HOST"
[ -n "$DB_USER" ] && export USER="$DB_USER"
[ -n "$DB_PASSWORD" ] && export PASSWORD="$DB_PASSWORD"
[ -n "$DB_PORT" ] && export PORT="$DB_PORT"
[ -n "$DB_NAME" ] && export DB_NAME="$DB_NAME"

# Ejecutar el entrypoint original de Odoo
exec /entrypoint.sh "$@"
