from odoo import _
from ..exceptions.webhook_exceptions import DuplicateMessageError
from ..utils.webhook_logger import WebhookLogger

import logging

_logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Service for duplicate detection and management"""
    
    def __init__(self, env):
        self.env = env
    
    def is_duplicate(self, message_id_provider_chat):
        """
        Check if message is duplicate using row-level locking.
        
        Args:
            message_id_provider_chat (str): Provider's message ID
            
        Returns:
            bool: True if duplicate, False if new
        """
        if not message_id_provider_chat:
            return False
        
        try:
            # Use row-level locking to prevent race conditions
            self.env.cr.execute(
                """
                SELECT id FROM mail_message
                WHERE message_id_provider_chat = %s
                FOR UPDATE NOWAIT
                """,
                (message_id_provider_chat,)
            )
            
            result = self.env.cr.fetchone()
            if result:
                WebhookLogger.log_duplicate_detected(message_id_provider_chat)
                return True
            
            return False
            
        except Exception as e:
            # If we can't acquire lock, assume duplicate to be safe
            WebhookLogger.log_lock_acquisition_failed(message_id_provider_chat, str(e))
            return True
    
    def check_final_duplicate(self, message_id_provider_chat):
        """
        Final duplicate check before creating message.
        
        Args:
            message_id_provider_chat (str): Provider's message ID
            
        Returns:
            mail.message: Existing message if found, None otherwise
        """
        if not message_id_provider_chat:
            return None
        
        existing = self.env["mail.message"].search([
            ('message_id_provider_chat', '=', message_id_provider_chat)
        ], limit=1)
        
        if existing:
            WebhookLogger.log_final_duplicate_check_found(message_id_provider_chat)
            return existing
        
        return None
    
    def cleanup_duplicates(self):
        """
        Utility method to clean up existing duplicate messages.
        Should be run manually if duplicates exist.
        """
        WebhookLogger.log_cleanup_start()
        
        # Find all messages with duplicates
        self.env.cr.execute("""
            SELECT message_id_provider_chat, array_agg(id ORDER BY id) as ids
            FROM mail_message 
            WHERE message_id_provider_chat IS NOT NULL
            GROUP BY message_id_provider_chat
            HAVING COUNT(*) > 1
        """)
        
        duplicates = self.env.cr.fetchall()
        cleaned_count = 0
        
        for message_id_provider, ids in duplicates:
            # Keep the first message, delete the rest
            keep_id = ids[0]
            delete_ids = ids[1:]
            
            WebhookLogger.log_duplicate_cleanup(message_id_provider, keep_id, delete_ids)
            
            # Delete duplicate messages
            self.env["mail.message"].browse(delete_ids).unlink()
            cleaned_count += len(delete_ids)
        
        WebhookLogger.log_cleanup_completed(len(duplicates), cleaned_count)
        
        return {
            "duplicate_groups": len(duplicates),
            "messages_cleaned": cleaned_count
        }
