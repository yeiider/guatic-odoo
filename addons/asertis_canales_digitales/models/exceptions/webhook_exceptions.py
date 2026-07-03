class ChannelCreationError(Exception):
    """Exception raised for errors in channel creation."""

    pass


class PartnerCreationError(Exception):
    """Exception raised for errors in partner creation."""

    pass


class WebhookProcessingError(Exception):
    """Exception raised for errors in webhook processing."""

    pass


class DuplicateMessageError(Exception):
    """Exception raised for duplicate messages in webhook processing."""

    pass
