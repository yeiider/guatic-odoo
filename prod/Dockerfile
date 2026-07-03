FROM odoo:18

USER root

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY prod/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --break-system-packages

# Copiar configuración de Odoo (evita bind-mount en Coolify)
COPY odoo.prod.conf /etc/odoo/odoo.conf

# Copiar addons custom directamente al contenedor
COPY addons /mnt/extra-addons

EXPOSE 8069 8072 8071

USER odoo
