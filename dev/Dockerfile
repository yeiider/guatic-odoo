
FROM odoo:18

# Cambiar a usuario root para instalar paquetes
USER root

# Instalar dependencias del sistema si es necesario
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*



# Instalar dependencias de Python desde requirements.txt
COPY requirements.txt /tmp/requirements.txt 
RUN pip3 install -r /tmp/requirements.txt --break-system-packages

# Exponer tanto el puerto HTTP como el de WebSockets
EXPOSE 8069 8072

# Volver al usuario odoo
USER odoo