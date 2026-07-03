# config/webhook_config.py
class WebhookConfig:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    DOWNLOAD_TIMEOUT = 30
    ALLOWED_MIME_TYPES = [...]
    DEFAULT_INTERNAL_USER_REF = "base.user_admin"
