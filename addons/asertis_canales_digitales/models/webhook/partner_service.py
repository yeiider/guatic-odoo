from ..payloads.base_event import ContactMetadata
from ..utils.webhook_logger import WebhookLogger
from ..exceptions.webhook_exceptions import PartnerCreationError

import logging

_logger = logging.getLogger(__name__)


class PartnerManagementService:
    """Service for managing partners/contacts from webhook events"""
    
    def __init__(self, env):
        self.env = env
    
    
    def find_or_create_partner(self, provider_name, payload):
        """
        Find or create a partner based on webhook payload.
        
        Args:
            provider_name (str): Name of the webhook provider
            payload: Webhook payload containing user information
            
        Returns:
            res.partner: The found or created partner
        """
        try:
            provider_data = self._build_provider_data(
                payload, provider_name
            )
            
            contact_metadata = self._build_contact_metadata(payload)
            
            partner = self.env["res.partner"].find_or_create_partner(
                provider_data=provider_data,
                contact_metadata=contact_metadata
            )
            
            if not partner:
                raise PartnerCreationError("Partner could not be found or created")
            
            WebhookLogger.log_partner_processed(partner.id, payload.user_id)
            return partner
            
        except Exception as e:
            raise PartnerCreationError(f"Error processing partner: {str(e)}")
    
    def _build_provider_data(self, payload, provider_name):
        """Build provider data dictionary"""
        channel_name = getattr(payload, 'channel_name', None) or provider_name
        
        return {
            "user_id": payload.user_id,
            "provider_name": provider_name,
            "user_name": getattr(payload, 'user_name', None),
            "user_channel": channel_name,
        }
    
    def _build_contact_metadata(self, payload):
        """Build contact metadata from payload"""
        if not hasattr(payload, 'message') or not hasattr(payload.message, 'contact'):
            return None
        
        contact = payload.message.contact
        if not contact:
            return None
        
        return ContactMetadata(
            first_name=getattr(contact, 'first_name', None),
            last_name=getattr(contact, 'last_name', None),
            phone_number=getattr(contact, 'phone_number', None),
            email=getattr(contact, 'email', None),
            profile_picture_url=getattr(contact, 'profile_picture_url', None),
        )

