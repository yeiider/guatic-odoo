#!/bin/bash
set -e

# =============================================================================
# Mapeo DB_HOST/DB_USER/DB_PASSWORD/DB_PORT/DB_NAME → HOST/USER/PASSWORD/PORT/DB_NAME
# para que el entrypoint original de Odoo los use (vía : ${HOST:=...})
#
# NOTA: NO exportamos PORT desde DB_PORT porque Coolify usa PORT para
# detectar el puerto del contenedor. El entrypoint original de Odoo
# por defecto usa PORT=5432 (si no está definido).
# =============================================================================

[ -n "$DB_HOST" ] && export HOST="$DB_HOST"
[ -n "$DB_USER" ] && export USER="$DB_USER"
[ -n "$DB_PASSWORD" ] && export PASSWORD="$DB_PASSWORD"
[ -n "$DB_NAME" ] && export DB_NAME="$DB_NAME"

# PORT no se exporta — el entrypoint original defaultea a 5432
# Si necesitas un DB_PORT distinto, agrégalo en el config file

# Ejecutar el entrypoint original de Odoo
exec /entrypoint.sh "$@"
