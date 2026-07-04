#!/bin/bash
set -e

# =============================================================================
# Entrypoint personalizado para Odoo en Coolify
# =============================================================================
# Pasa los parámetros de BD directamente a Odoo como CLI args,
# evitando el entrypoint original que tiene conflictos con PORT=8069
# y otras variables de Coolify.
# =============================================================================

ODOO_RC="${ODOO_RC:-/etc/odoo/odoo.conf}"

# Construir argumentos para wait-for-psql.py (solo conexión, sin --database)
WAIT_ARGS=()

if [ -n "$DB_HOST" ]; then
    WAIT_ARGS+=("--db_host=$DB_HOST")
fi

if [ -n "$DB_PORT" ]; then
    WAIT_ARGS+=("--db_port=$DB_PORT")
fi

if [ -n "$DB_USER" ]; then
    WAIT_ARGS+=("--db_user=$DB_USER")
fi

if [ -n "$DB_PASSWORD" ]; then
    WAIT_ARGS+=("--db_password=$DB_PASSWORD")
fi

# Construir argumentos para Odoo
# NOTA: NO pasamos --database para que Odoo muestre el gestor de creación
# de BD cuando list_db=True. La BD se asigna desde la URL o se crea en la UI.
ODOO_ARGS=("${WAIT_ARGS[@]}")

# Esperar a que PostgreSQL esté disponible
if command -v wait-for-psql.py &> /dev/null; then
    wait-for-psql.py "${WAIT_ARGS[@]}" --timeout=30
fi

# Ejecutar Odoo directamente con los argumentos de BD
exec odoo --config="$ODOO_RC" "${ODOO_ARGS[@]}" "$@"
