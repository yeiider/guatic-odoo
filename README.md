# Sistema Omnicanal de Mensajería para Odoo 18

## Tabla de contenido

- [Sistema Omnicanal de Mensajería para Odoo 18](#sistema-omnicanal-de-mensajería-para-odoo-18)
  - [Tabla de contenido](#tabla-de-contenido)
  - [Descripción general](#descripción-general)
  - [Arquitectura](#arquitectura)
    - [Puertos](#puertos)
  - [Requisitos](#requisitos)
  - [Instalación y configuración](#instalación-y-configuración)
  - [Flujo de procesamiento de mensajes](#flujo-de-procesamiento-de-mensajes)
  - [Gestión desde la interfaz](#gestión-desde-la-interfaz)
    - [Proveedores](#proveedores)
    - [Habilidades](#habilidades)
  - [Despliegue con Docker y Nginx Proxy Manager](#despliegue-con-docker-y-nginx-proxy-manager)
    - [Desarrollo](#desarrollo)
    - [Producción](#producción)
      - [Nginx Proxy Manager](#nginx-proxy-manager)
      - [Configuración avanzada para WebSocket y longpolling](#configuración-avanzada-para-websocket-y-longpolling)
      - [Instalación de Nginx Proxy Manager](#instalación-de-nginx-proxy-manager)
  - [Estructura del módulo](#estructura-del-módulo)

---

## Descripción general

Este módulo para **Odoo 18** permite integrar múltiples canales digitales (WhatsApp, Instagram, X, Telegram, Facebook, etc.) con el sistema de mensajería de Odoo, utilizando *webhooks* proporcionados por servicios de chatbot como **HeyNow**, **Botpress**, **Meta**, entre otros.

Permite recibir, validar, enrutar, responder y administrar mensajes entrantes y salientes dentro de Odoo mediante una estructura configurable y extensible.

---

## Arquitectura

```
                         ┌────────────────────┐
                         │  NGINX Proxy Mgr   │
                         │  (81: Admin Panel) │
                         └────────┬───────────┘
                                  │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
       ┌──────▼──────┐    ┌──────▼──────┐     ┌─────▼─────┐
       │ HTTP : 80   │    │ HTTPS : 443 │     │ Longpoll  │
       │ WS + SSL    │    │ Certificados│     │  : 8072   │
       └──────┬──────┘    └──────┬──────┘     └─────┬─────┘
              │                  │                  │
              └──────────────────┴──────────────────┘
                             ↓ proxy-network
┌─────────────────────────────────────────────────────────────────────┐
│                        APP: omnichannel                             │
│                                                                     │
│ ┌────────────────────┐   ┌────────────────────┐                     │
│ │   Odoo (8069/8072) │<--│ PostgreSQL (5432)   │                     │
│ └────────────────────┘   └────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Puertos

* `80` → HTTP (Nginx Server)
* `443` → HTTPS (SSL)
* `81` → Admin de Nginx Proxy Manager
* `20` → SSH (externo)
* `8069`, `8072` → Odoo (web y longpolling)
* `5432` → PostgreSQL

---

## Requisitos

* Odoo 18
* PostgreSQL 13 o superior
* Python 3.10+
* Librería `queue_job`
* Docker y Docker Compose

---

## Instalación y configuración

1. Clonar el módulo en la carpeta de addons de Odoo.
2. Agregarlo al archivo de configuración `odoo.conf` dentro del parámetro `addons_path`.
3. Reiniciar Odoo y activar el modo desarrollador.
4. Instalar el módulo desde la interfaz.

---

## Flujo de procesamiento de mensajes

1. **Recepción del webhook**

   El webhook es recibido en la ruta:

   ```
   /webhook/chat/<string:provider_name>
   ```

   El payload JSON se procesa a través de `BaseEvent`.

2. **Validaciones previas**

   * Mensaje procesable.
   * Canal habilitado.
   * Proveedor autenticado.
   * Restricciones específicas por proveedor (plataforma, bots, etc.).

3. **Paso a la cola `queue_job`**

   * Se evita el loop de mensajes.
   * Validación de duplicados (por UUID).
   * Verificación de contenido del mensaje.

4. **Contacto (`res.partner`)**

   Se busca o crea el contacto con base en teléfono, email, ID, etc.

5. **Usuarios internos por habilidades**

   Se buscan agentes internos según habilidades asignadas.

6. **Canal (`mail.channel`)**

   Se crea o reutiliza un canal asociado al contacto y proveedor.

7. **Mensaje (`mail.message`)**

   * Se limpia HTML.
   * Se gestionan archivos adjuntos.
   * Se postea el mensaje en Odoo.

8. **Respuesta desde Odoo al proveedor**

   * El mensaje se adapta al formato del proveedor.
   * Se envía por API externa correspondiente.

---

## Gestión desde la interfaz

### Proveedores

* Crear, editar y eliminar proveedores.
* Atributos:

  * Nombre
  * Tipo de proveedor (HeyNow, Meta, Botpress...)
  * Canales permitidos (WhatsApp, Messenger...)
  * URL base de respuesta
  * Configuración adicional (JSON)
  * Token de autenticación

### Habilidades

* Crear habilidades de forma individual o masiva.
* Usar plantilla Excel para importación masiva.
* Asignar habilidades a usuarios internos desde su ficha.

---

## Despliegue con Docker y Nginx Proxy Manager

### Desarrollo

* Contenedor de Odoo y PostgreSQL con `docker-compose`.

(Ver configuración en el bloque anterior)

### Producción

#### Nginx Proxy Manager

Para exponer tu instancia Odoo de forma segura usando tu dominio personalizado:

1. Crea un proxy host en Nginx Proxy Manager
2. Usa el dominio (por ejemplo `odoo.fraster.site`)
3. Establece el esquema como `http`, y apunta a `odoo:8069`
4. Activa WebSocket Support y Block Common Exploits
5. (Opcional) Activa SSL y configura el certificado Let's Encrypt

#### Configuración avanzada para WebSocket y longpolling

En la sección de personalización de Nginx (custom locations), incluye:

```nginx
location /websocket {
    proxy_pass http://odoo:8072;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}

location /longpolling {
    proxy_pass http://odoo:8072;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}
```

#### Instalación de Nginx Proxy Manager

Puedes ver instrucciones detalladas en su [documentación oficial](https://nginxproxymanager.com/guide/).

---

## Estructura del módulo

```
📁asertis_canales_digitales
├── controllers
│   └── webhook.py
├── data
│   └── chat_channel_type.xml
├── models
│   ├── exceptions
│   │   └── webhook_exceptions.py
│   ├── heynow
│   │   ├── payload.py
│   │   ├── provider.py
│   │   ├── service.py
│   │   ├── types.py
│   ├── payloads
│   │   ├── base_event.py
│   │   └── dispatcher.py
│   ├── provider
│   │   ├── handlers
│   │   │   ├── file_handler.py
│   │   │   └── message_builder.py
│   │   └── strategies
│   │       ├── base_strategy.py
│   │       ├── strategy_factory.py
│   ├── services
│   │   └── provider_service.py
│   ├── utils
│   │   ├── avatar.py
│   │   ├── res_partner.py
│   │   └── webhook_logger.py
│   └── webhook
│       ├── attachment_service.py
│       ├── channel_service.py
│       ├── duplicate_service.py
│       ├── partner_service.py
│       └── webhook_config.py
├── views
│   ├── chat_provider_views.xml
│   ├── provider_skill_views.xml
│   └── menu.xml
├── static
│   └── description/icon.png
│   └── img/providers/*.png
├── __manifest__.py
└── __init__.py
```

---
