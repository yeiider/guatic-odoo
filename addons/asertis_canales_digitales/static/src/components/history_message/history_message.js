/** @odoo-module **/
import { Component } from "@odoo/owl";

export class HistoryMessage extends Component {
  static template = "mail.HistoryMessage";
  static props = {
    message: Object,
    chatHistoryService: Object,
  };

  get formattedTimestamp() {
    return this.props.chatHistoryService.formatTimestamp(
      this.props.message.timestamp
    );
  }

  get hasAttachments() {
    return (
      this.props.message.attachments &&
      this.props.message.attachments.length > 0
    );
  }

  get isImageMessage() {
    return this.props.message.message_type === "image";
  }

  get isFileMessage() {
    return this.props.message.message_type === "file";
  }

  get isSystemMessage() {
    return this.props.message.message_type === "system";
  }

  onDownloadAttachment(attachment) {
    if (attachment.download_url) {
      window.open(attachment.download_url, "_blank");
    }
  }

  getFileIcon(mimetype) {
    if (!mimetype) return "fa-file";

    const typeMap = {
      "image/": "fa fa-fw fa-lg fa-file-image",
      "video/": "fa fa-fw fa-lg fa-file-video",
      "audio/": "fa fa-fw fa-lg fa-file-audio",
      "text/": "fa fa-fw fa-lg fa-file-text",
      "application/pdf": "fa fa-fw fa-lg fa-file-pdf",
      "application/zip": "fa fa-fw fa-lg fa-file-archive",
      "application/x-zip": "fa fa-fw fa-lg fa-file-archive",
      "application/x-rar": "fa fa-fw fa-lg fa-file-archive",
      "application/x-7z": "fa fa-fw fa-lg fa-file-archive",
      "application/msword": "fa fa-fw fa-lg fa-file-word",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        "fa fa-fw fa-lg fa-file-word",
      "application/vnd.ms-excel": "fa fa-fw fa-lg fa-file-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        "fa fa-fw fa-lg fa-file-excel",
      "application/vnd.ms-powerpoint": "fa fa-fw fa-lg fa-file-powerpoint",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        "fa fa-fw fa-lg fa-file-powerpoint",
    };

    for (const [type, icon] of Object.entries(typeMap)) {
      if (mimetype.startsWith(type) || mimetype === type) {
        return icon;
      }
    }

    return "fa-file";
  }

  getMimeTypeExtension(mimeType) {
    if (!mimeType) return "unknown";

    const mimeToExtension = {
      // Imágenes
      "image/jpeg": "jpg",
      "image/jpg": "jpg",
      "image/png": "png",
      "image/gif": "gif",
      "image/webp": "webp",
      "image/svg+xml": "svg",
      "image/bmp": "bmp",
      "image/tiff": "tiff",
      "image/x-icon": "ico",

      // Videos
      "video/mp4": "mp4",
      "video/avi": "avi",
      "video/quicktime": "mov",
      "video/x-msvideo": "avi",
      "video/webm": "webm",
      "video/x-flv": "flv",
      "video/3gpp": "3gp",

      // Audio
      "audio/mpeg": "mp3",
      "audio/mp3": "mp3",
      "audio/wav": "wav",
      "audio/ogg": "ogg",
      "audio/aac": "aac",
      "audio/flac": "flac",
      "audio/x-ms-wma": "wma",

      // Documentos
      "text/plain": "txt",
      "text/html": "html",
      "text/css": "css",
      "text/javascript": "js",
      "text/csv": "csv",
      "text/xml": "xml",
      "application/json": "json",

      // PDFs
      "application/pdf": "pdf",

      // Microsoft Office
      "application/msword": "doc",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        "docx",
      "application/vnd.ms-excel": "xls",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        "xlsx",
      "application/vnd.ms-powerpoint": "ppt",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        "pptx",

      // Archivos comprimidos
      "application/zip": "zip",
      "application/x-zip": "zip",
      "application/x-zip-compressed": "zip",
      "application/x-rar": "rar",
      "application/x-rar-compressed": "rar",
      "application/x-7z-compressed": "7z",
      "application/gzip": "gz",
      "application/x-tar": "tar",

      // Otros formatos comunes
      "application/xml": "xml",
      "application/javascript": "js",
      "application/rtf": "rtf",
      "application/vnd.oasis.opendocument.text": "odt",
      "application/vnd.oasis.opendocument.spreadsheet": "ods",
      "application/vnd.oasis.opendocument.presentation": "odp",
    };

    // Normalizar el MIME type
    const normalizedMimeType = mimeType.toLowerCase().split(";")[0].trim();

    // Buscar coincidencia exacta
    if (mimeToExtension[normalizedMimeType]) {
      return mimeToExtension[normalizedMimeType];
    }

    // Fallback: intentar extraer de la parte después de '/'
    const parts = normalizedMimeType.split("/");
    if (parts.length === 2) {
      const subtype = parts[1];

      // Casos especiales comunes
      const commonSubtypes = {
        jpeg: "jpg",
        mpeg: "mp3",
        quicktime: "mov",
        "x-msvideo": "avi",
      };

      return commonSubtypes[subtype] || subtype;
    }

    return "unknown";
  }

  formatFileSize(size) {
    if (!size) return "";

    const units = ["B", "KB", "MB", "GB"];
    let unitIndex = 0;
    let fileSize = size;

    while (fileSize >= 1024 && unitIndex < units.length - 1) {
      fileSize /= 1024;
      unitIndex++;
    }

    return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
  }
}
