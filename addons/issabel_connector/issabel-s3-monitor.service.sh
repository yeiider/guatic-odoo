[Unit]
Description=Issabel S3 Real-time Recording Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/issabel-backup/realtime_monitor.sh
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

# Variables de entorno si son necesarias
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="HOME=/root"

[Install]
WantedBy=multi-user.target



