FROM odoo:18

USER root

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY prod/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --break-system-packages

# Copiar configuración de Odoo
COPY odoo.prod.conf /etc/odoo/odoo.conf

# Copiar addons custom
COPY addons /mnt/extra-addons

# Copiar entrypoint personalizado que mapea variables
COPY prod/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]

EXPOSE 8069 8072 8071

USER odoo
