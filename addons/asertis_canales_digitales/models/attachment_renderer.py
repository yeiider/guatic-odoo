from odoo import models, _
from typing import List
import time
import mimetypes


class AttachmentRenderer(models.AbstractModel):
    _name = "attachment.renderer"
    _description = "Renderizador de Attachments para Odoo 18"

    def generate_message_body_native(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Genera el body del mensaje usando plantillas nativas de Odoo 18
        """
        if not attachments:
            return original_body or ""

        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                template_name = "mail.message_attachment_list"
                template_exists = self.env["ir.ui.view"].search(
                    [("key", "=", template_name)], limit=1
                )

                if template_exists:
                    template = (
                        self.env["ir.ui.view"]
                        .sudo()
                        ._render_template(
                            template_name,
                            {
                                "attachments": attachments,
                            },
                        )
                    )

                    body_parts = [original_body or "", template]
                    return "<br/>".join(filter(None, body_parts))
                else:
                    return self.generate_message_body_manual(original_body, attachments)

            except Exception as e:
                if attempt < max_retries - 1 and "concurrency" in str(e).lower():
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    return self.generate_message_body_manual(original_body, attachments)

        return original_body or ""

    def generate_message_body_manual(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Genera el contenido del body del mensaje usando renderizado manual
        compatible con Odoo 18
        """
        if not attachments:
            return original_body or ""

        body_parts = [original_body or ""]

        attachment_html = self._generate_odoo18_attachments_html(attachments)
        if attachment_html:
            body_parts.append(attachment_html)

        return "<br/>".join(filter(None, body_parts))

    def _generate_odoo18_attachments_html(self, attachments: List[models.Model]) -> str:
        """
        Genera HTML para attachments usando la estructura actualizada para Odoo 18
        """
        if not attachments:
            return ""

        attachment_items = []

        for attachment in attachments:
            attachment_html = self._render_single_attachment_odoo18(attachment)
            if attachment_html:
                attachment_items.append(attachment_html)

        if not attachment_items:
            return ""

        return f"""
        <div class="o_mail_attachment_list d-flex flex-wrap gap-2 mt-2">
            {"".join(attachment_items)}
        </div>
        """

    def _render_single_attachment_odoo18(self, attachment) -> str:
        """
        Renderiza un attachment individual usando la estructura actualizada de Odoo 18
        """
        mimetype = attachment.mimetype or ""
        file_url = f"/web/content/{attachment.id}"
        download_url = f"/web/content/{attachment.id}?download=true"
        if hasattr(attachment, "get_base_url") and attachment.get_base_url:
            base_url = attachment.get_base_url()
            if base_url:
                file_url = base_url + file_url

        if mimetype.startswith("image/"):
            return self._render_image_attachment_odoo18(
                attachment, file_url, download_url
            )
        else:
            return self._render_generic_attachment_odoo18(attachment, download_url)

    def _render_image_attachment_odoo18(
        self, attachment, file_url, download_url
    ) -> str:
        """
        Renderiza imagen usando estructura compatible con Odoo 18
        """
        return f"""
        <div class="o_mail_attachment o_mail_attachment_image position-relative d-inline-block rounded overflow-hidden">
            <div class="o_mail_attachment_image_container position-relative">
                <img class="o_mail_attachment_image img-fluid rounded" 
                     src="{file_url}"
                     alt="{attachment.name}"
                     title="{attachment.name}"
                     style="max-width: min(100%, 300px); max-height: 200px; object-fit: cover;">
                
                <div class="o_mail_attachment_overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center opacity-0 hover-opacity-100 bg-dark bg-opacity-50 rounded">
                    <div class="btn-group">
                        <a href="{file_url}" target="_blank" 
                           class="btn btn-sm btn-light rounded-circle me-1" 
                           title="Ver imagen">
                            <i class="fa fa-eye"></i>
                        </a>
                        <a href="{download_url}" 
                           class="btn btn-sm btn-light rounded-circle" 
                           title="Descargar" 
                           download="{attachment.name}">
                            <i class="fa fa-download"></i>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """

    def _render_generic_attachment_odoo18(self, attachment, download_url) -> str:
        """
        Renderiza attachment genérico usando estructura compatible con Odoo 18
        """
        # Obtener extensión y tipo de archivo
        extension = mimetypes.guess_extension(attachment.mimetype) or ""
        if not extension and attachment.name:
            extension = (
                "." + attachment.name.split(".")[-1] if "." in attachment.name else ""
            )

        file_type = extension.lstrip(".").upper() if extension else "FILE"

        return f"""
        <div class="o_mail_attachment o_mail_attachment_file d-flex align-items-center border rounded p-2 bg-light">
            <div class="o-mail-AttachmentCard-image o_image flex-shrink-0 m-1" role="menuitem" aria-label="Vista previa" tabindex="-1" data-mimetype={attachment.mimetype}>
            </div>
            
            <div class="o_mail_attachment_details flex-grow-1 min-width-0">
                <div class="o_mail_attachment_name text-truncate fw-bold">
                    {attachment.name}
                </div>
                <div class="o_mail_attachment_info d-flex align-items-center">
                    <small class="text-muted me-2">{file_type}</small>
                    {self._format_file_size(attachment.file_size) if hasattr(attachment, 'file_size') and attachment.file_size else ''}
                </div>
            </div>
            
            <div class="o_mail_attachment_actions ms-2">
                <a href="{download_url}" 
                   class="btn btn-sm btn-outline-primary" 
                   title="Descargar archivo" 
                   download="{attachment.name}">
                    <i class="fa fa-download"></i>
                </a>
            </div>
        </div>
        """

    def _get_file_icon_class(self, mimetype, extension):
        """
        Retorna la clase CSS del icono basado en el tipo de archivo
        """
        if not mimetype:
            return "fa fa-file"

        if mimetype.startswith("image/"):
            return "fa fa-file-image"
        elif mimetype.startswith("video/"):
            return "fa fa-file-video"
        elif mimetype.startswith("audio/"):
            return "fa fa-file-audio"
        elif mimetype == "application/pdf":
            return "fa fa-file-pdf text-danger"
        elif mimetype in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return "fa fa-file-word text-primary"
        elif mimetype in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            return "fa fa-file-excel text-success"
        elif mimetype in [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]:
            return "fa fa-file-powerpoint text-warning"
        elif mimetype in [
            "application/zip",
            "application/x-zip-compressed",
            "application/x-rar-compressed",
        ]:
            return "fa fa-file-archive text-info"
        elif mimetype.startswith("text/"):
            return "fa fa-file-text"
        else:
            return "fa fa-file"

    def _format_file_size(self, size_bytes):
        """
        Formatea el tamaño del archivo en formato legible
        """
        if not size_bytes:
            return ""

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def generate_message_body(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Método de compatibilidad que llama al método manual
        """
        return self.generate_message_body_manual(original_body, attachments)
