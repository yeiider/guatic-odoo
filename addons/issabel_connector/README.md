# Issabel Connector - Estadísticas en Tiempo Real

## 📋 Descripción

Módulo de Odoo 18 que se integra con Issabel/Asterisk a través de AMI (Asterisk Manager Interface) para obtener estadísticas de colas en tiempo real.

## ✨ Características

### 📊 Estadísticas en Tiempo Real
- **Llamadas en espera**: Cantidad y tiempo de espera en vivo
- **Agentes disponibles**: Estados (disponible, en llamada, pausado, offline)
- **Nivel de servicio (SLA)**: Porcentaje de cumplimiento en tiempo real
- **Tiempos promedio**: Espera y conversación
- **Llamadas del día**: Completadas y abandonadas

### 🔄 Actualización Manual
- Botón "Actualizar" en cada cola
- Botón "Actualizar Todas" para todas las colas
- Actualización automática cada 30 segundos (configurable)

### 📞 Monitoreo de Llamadas
- Llamadas en espera con posición en cola
- Tiempo de espera en segundos
- Estado de conexión con agentes

### 👥 Gestión de Agentes
- Estado actual de cada agente
- Llamadas tomadas
- Motivo de pausa
- Última actividad

## 🚀 Instalación

### 1. Requisitos Previos

```bash
# Instalar librería AMI de Python
pip3 install asterisk-ami
```

### 2. Instalar Módulo

1. Copiar la carpeta `issabel_connector` a `/odoo/addons/`
2. Actualizar lista de aplicaciones en Odoo
3. Instalar "Issabel Connector - Real Time Statistics"

### 3. Configuración de Issabel/Asterisk

Editar `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[odoo]
secret = tu_password_seguro
read = all
write = all
```

Reiniciar AMI:
```bash
asterisk -rx "manager reload"
```

### 4. Configuración en Odoo

1. Ir a **Issabel Connector > Configuración**
2. Crear/editar configuración:
   - Host AMI: IP del servidor Asterisk (ej: 192.168.1.100)
   - Puerto AMI: 5038
   - Usuario AMI: odoo
   - Contraseña AMI: tu_password_seguro
3. Clic en "🔌 Probar Conexión"
4. El servicio se iniciará automáticamente

## 📱 Uso

### Ver Estadísticas de Colas

1. **Issabel Connector > Tiempo Real > Estadísticas de Colas**
2. Vista Kanban muestra dashboard en tiempo real
3. Clic en "Actualizar" para refrescar datos

### Ver Llamadas en Espera

1. **Issabel Connector > Tiempo Real > Llamadas en Espera**
2. Muestra llamadas actualmente esperando
3. Se actualiza automáticamente cada 30 segundos

### Ver Miembros de Colas

1. **Issabel Connector > Tiempo Real > Miembros de Colas**
2. Estado actual de todos los agentes
3. Filtros por disponibilidad

## 🎨 Vistas Disponibles

### Dashboard de Colas (Kanban)
- **Llamadas en espera**: Destacado en grande
- **Agentes**: 4 contadores (disponibles, en llamada, pausados, offline)
- **Estadísticas del día**: Completadas y abandonadas
- **Tiempos promedio**: Espera y conversación
- **Nivel de servicio**: Badge con colores según rendimiento
- **Botón actualizar**: En cada tarjeta

### Lista de Colas
- Tabla con todas las métricas
- Botón "Actualizar Todas" en header
- Decoraciones por umbrales

### Llamadas en Espera
- Vista Kanban: Tarjetas por llamada
- Badges de color según tiempo de espera:
  - 🟢 Verde: < 30 segundos
  - 🟡 Amarillo: 30-60 segundos
  - 🔴 Rojo: > 60 segundos

## 🔧 Configuración Avanzada

### Cambiar Frecuencia de Actualización

Editar el cron en **Configuración > Técnico > Automatización > Acciones Planificadas**:
- Buscar "Actualizar Estadísticas de Colas (AMI)"
- Cambiar intervalo (default: 30 segundos)

### Umbrales de Alerta

Modificar en `queue_statistics_views.xml`:

```xml
<!-- Cambiar colores según umbrales -->
<field name="calls_waiting" decoration-danger="calls_waiting > 5" 
       decoration-warning="calls_waiting > 2"/>
```

## 📊 Eventos AMI Capturados

| Evento | Descripción | Uso |
|--------|-------------|-----|
| `QueueParams` | Estadísticas generales de cola | Métricas principales |
| `QueueMember` | Información de agentes | Estado de agentes |
| `QueueEntry` | Llamadas en espera | Lista de espera |
| `QueueCallerJoin` | Cliente se une a cola | Nueva llamada |
| `QueueCallerLeave` | Cliente sale de cola | Llamada atendida |
| `QueueCallerAbandon` | Cliente abandona | Llamada perdida |
| `AgentConnect` | Agente conecta | Inicio de conversación |
| `AgentComplete` | Agente finaliza | Fin de conversación |
| `QueueMemberPaused` | Agente en pausa | Cambio de estado |

## 🐛 Troubleshooting

### El servicio AMI no se conecta

**Problema**: Error al conectar con AMI

**Soluciones**:
1. Verificar que Asterisk esté corriendo: `asterisk -rx "core show version"`
2. Verificar configuración de manager.conf
3. Verificar firewall: `telnet <host> 5038`
4. Revisar logs de Odoo: `/var/log/odoo/odoo-server.log`

### No aparecen estadísticas

**Problema**: Las vistas están vacías

**Soluciones**:
1. Verificar que el servicio AMI esté corriendo
2. Presionar botón "Actualizar"
3. Ejecutar manualmente: `env['ami.service']._request_all_queue_statistics()`
4. Verificar que las colas existan en Issabel

### Las estadísticas no se actualizan

**Problema**: Datos estancados

**Soluciones**:
1. Verificar que el cron esté activo
2. Reiniciar servicio AMI desde configuración
3. Revisar logs para errores de thread

### Eventos no se capturan

**Problema**: No se registran llamadas

**Soluciones**:
1. Verificar eventos en Asterisk CLI: `asterisk -rvvv`
2. Ejecutar: `manager show eventq`
3. Verificar permisos de usuario AMI en manager.conf

## 📈 Rendimiento

### Optimizaciones Implementadas

- **Cursores independientes**: Cada evento usa su propio cursor
- **Commits inmediatos**: Los datos se guardan inmediatamente
- **Thread daemon**: No bloquea el shutdown de Odoo
- **Reconexión automática**: Se reconecta cada 5 segundos si falla
- **Limpieza automática**: Cron elimina datos antiguos

### Recomendaciones

- Para más de 50 colas, aumentar intervalo de actualización a 60 segundos
- Monitorear uso de CPU del thread AMI
- Considerar usar Redis para caché si hay muchos agentes

## 🔐 Seguridad

### Permisos por Modelo

- **Usuarios normales**: Solo lectura de estadísticas
- **Administradores**: Gestión completa de configuración
- **Sistema**: Control del servicio AMI

### Mejores Prácticas

1. Usar usuario AMI dedicado con permisos mínimos
2. Contraseñas fuertes para AMI
3. Firewall que permita solo IP de Odoo al puerto 5038
4. Encriptar tráfico con SSH tunnel si es remoto

## 📝 Estructura del Módulo

```
issabel_connector/
├── __init__.py
├── __manifest__.py
├── hooks.py
├── models/
│   ├── __init__.py
│   ├── issabel_config.py
│   ├── issabel_call_log.py
│   ├── issabel_agent_status.py
│   ├── issabel_queue_statistics.py
│   └── ami_service_model.py
├── views/
│   ├── issabel_config_views.xml
│   ├── call_log_views.xml
│   ├── agent_status_views.xml
│   ├── queue_statistics_views.xml
│   └── issabel_menus.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── ir_cron.xml
└── README.md
```

## 🤝 Contribuir

Para reportar bugs o solicitar features, crear un issue en el repositorio.

## 📄 Licencia

LGPL-3

## 👨‍💻 Autor

Tu Empresa

## 📞 Soporte

Para soporte técnico, contactar a soporte@tuempresa.com