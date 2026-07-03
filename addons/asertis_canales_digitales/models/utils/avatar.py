import base64
import os

from odoo.tools.misc import file_path

PROVIDER_AVATAR_MAP = {
    "whatsapp": "whatsapp.png",
    "instagram": "instagram.png",
    "messenger": "messenger.png",
    "telegram": "telegram.png",
    "facebook": "facebook.png",
    "twitter": "twitter.png",
    "web": "web.png",
    "email": "email.png",
    "sms": "sms.png",
    "linkedin": "linkedin.png",
    "discord": "discord.png",
    "signal": "signal.png",
    "chatbot": "chatbot.png",
    "generic": "generic.png",
}


def get_provider_avatar(provider_name):
    """
    Retrieve the avatar image for a given provider as a base64-encoded string.
    """
    if not provider_name:
        return False

    provider_key = provider_name.lower().strip()
    image_file = PROVIDER_AVATAR_MAP.get(provider_key) or PROVIDER_AVATAR_MAP.get(
        "generic"
    )

    if not image_file:
        return False

    try:
        image_path = file_path(
            "asertis_canales_digitales", f"static/img/providers/{image_file}"
        )
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read())
    except Exception:
        return False

    return False
