from . import models
from . import controllers


def assign_uuids_to_old_messages(env):
    """
    Post-init hook que asigna UUIDs únicos a todos los mensajes existentes.
    """
    import uuid

    messages = env["mail.message"].sudo().search([])

    for message in messages:
        message.message_id_provider_chat = str(uuid.uuid4())

