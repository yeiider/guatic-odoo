from logging import getLogger

_logger = getLogger(__name__)


class WebhookLogger:
    @staticmethod
    def log_processing_start(provider_name, user_id, channel_name):
        _logger.info(
            "Webhook processing started",
            extra={
                "provider": provider_name,
                "user_id": user_id,
                "channel": channel_name,
            },
        )

    @staticmethod
    def log_processing_error(provider_name, error_message):
        _logger.error(
            "Webhook processing error for provider %s: %s", provider_name, error_message
        )

    @staticmethod
    def log_file_processing_failed(file_name):
        _logger.warning("File processing failed for file: %s", file_name)

    @staticmethod
    def log_file_downloaded(file_name, file_size):
        _logger.info(
            "File downloaded successfully: %s (%d bytes)", file_name, file_size
        )
