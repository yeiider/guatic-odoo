from ..utils.webhook_logger import WebhookLogger
from ..exceptions.webhook_exceptions import FileProcessingError
from .webhook_config import WebhookConfig
from ..payloads.base_event import FileEvent
from typing import List

import logging
import requests
import base64
import mimetypes
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


class AttachmentProcessingService:
    """Service for processing file attachments from webhook events"""

    def __init__(self, env):
        self.env = env
        self.config = WebhookConfig()

    def process_message_files(self, channel, files: List[FileEvent]) -> List[int]:
        """
        Process a list of FileEvent objects and create attachments.

        Args:
            channel: The discuss.channel record
            files: List of FileEvent objects

        Returns:
            List[int]: List of attachment IDs created
        """
        if not files:
            return []

        attachment_ids = []

        try:
            for file_event in files:
                attachment = self._create_attachment_from_file_event(
                    channel, file_event
                )
                if attachment:
                    attachment_ids.append(attachment.id)
                else:
                    WebhookLogger.log_file_processing_failed(file_event.name)

            WebhookLogger.log_files_processed(len(files), len(attachment_ids))
            return attachment_ids

        except Exception as e:
            WebhookLogger.log_file_processing_error(str(e))
            return attachment_ids

    def _create_attachment_from_file_event(self, channel, file_event: FileEvent):
        """
        Create ir.attachment from FileEvent.
        Handles both URLs and base64 data.
        """
        try:
            if not self._validate_file_event(file_event):
                return None

            if file_event.url:
                return self._download_and_create_attachment(file_event, channel)
            elif file_event.datas:
                return self._create_attachment_from_data(channel, file_event)
            else:
                WebhookLogger.log_file_event_no_data(file_event.name)
                return None

        except Exception as e:
            raise FileProcessingError(
                f"Error processing FileEvent {file_event.name}: {str(e)}"
            )

    def _download_and_create_attachment(self, file_event: FileEvent, channel):
        """Download file from URL and create attachment"""
        try:
            response = requests.get(
                file_event.url, timeout=self.config.DOWNLOAD_TIMEOUT
            )
            response.raise_for_status()

            file_data_b64 = base64.b64encode(response.content).decode("utf-8")
            mimetype = self._determine_mimetype(file_event, response)
            name = self._determine_filename(file_event)
            attachment_data = self._build_attachment_data(
                file_event, name, file_data_b64, mimetype, channel
            )

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            WebhookLogger.log_file_downloaded(file_event.url, attachment.id)
            return attachment

        except requests.RequestException as e:
            raise FileProcessingError(f"Error downloading file: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"Error processing downloaded file: {str(e)}")

    def _create_attachment_from_data(self, channel, file_event: FileEvent):
        """Create attachment from base64 data"""
        try:
            datas = file_event.datas

            # Handle data URLs
            if datas.startswith("data:"):
                mimetype_part = datas.split(";")[0].split(":")[1]
                if not file_event.mimetype:
                    file_event.mimetype = mimetype_part
                datas = datas.split(",")[1]

            # Determine mimetype
            mimetype = file_event.mimetype
            if not mimetype and file_event.name:
                mimetype, _ = mimetypes.guess_type(file_event.name)
                mimetype = mimetype or "application/octet-stream"

            # Create attachment
            attachment_data = self._build_attachment_data(
                file_event, file_event.name or "webhook_file", datas, mimetype, channel
            )

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            WebhookLogger.log_file_created_from_data(file_event.name, attachment.id)
            return attachment

        except Exception as e:
            raise FileProcessingError(f"Error creating attachment from data: {str(e)}")

    def _validate_file_event(self, file_event: FileEvent) -> bool:
        """Validate FileEvent has minimum required data"""
        if not file_event.name:
            return False

        if not file_event.url and not file_event.datas:
            return False

        # Validate base64 data if present
        if file_event.datas:
            try:
                data_to_validate = file_event.datas
                if data_to_validate.startswith("data:"):
                    data_to_validate = data_to_validate.split(",")[1]
                # Try to decode to validate
                base64.b64decode(data_to_validate)
                return True
            except Exception:
                return False

        return True

    def _determine_mimetype(self, file_event, response):
        """Determine the mimetype for the file"""
        # Priority: file_event.mimetype > response headers > guess from URL/name
        mimetype = file_event.mimetype
        if not mimetype:
            mimetype = response.headers.get("content-type")
        if not mimetype:
            mimetype, _ = mimetypes.guess_type(file_event.url or file_event.name)
        return mimetype or "application/octet-stream"

    def _determine_filename(self, file_event):
        """Determine the filename for the file"""
        if file_event.name:
            return file_event.name

        # Extract from URL
        parsed_url = urlparse(file_event.url)
        path = parsed_url.path
        if isinstance(path, bytes):
            path = path.decode("utf-8", errors="replace")

        filename = path.split("/")[-1] or "downloaded_file"
        return filename

    def _build_attachment_data(self, file_event, name, datas, mimetype, channel):
        """Build attachment data dictionary"""
        attachment_data = {
            "name": name,
            "type": getattr(file_event, "type", "binary"),
            "datas": datas,
            "res_model": "discuss.channel",
            "res_id": channel.id if channel else None,
            "mimetype": mimetype,
        }

        # Add optional fields
        if hasattr(file_event, "url") and file_event.url:
            attachment_data["url"] = file_event.url
        if hasattr(file_event, "description") and file_event.description:
            attachment_data["description"] = file_event.description
        if hasattr(file_event, "access_token") and file_event.access_token:
            attachment_data["access_token"] = file_event.access_token
        if hasattr(file_event, "checksum") and file_event.checksum:
            attachment_data["checksum"] = file_event.checksum

        return attachment_data
