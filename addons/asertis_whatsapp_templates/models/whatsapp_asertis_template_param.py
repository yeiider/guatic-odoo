from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class WatsappAsertisTemplateParam(models.Model):
    _name = "whatsapp.asertis.template.param"
    _description = "Parámetros de Plantillas whatsapp Asertis"
    _order = "sequence, id"
    _rec_name = "name"

    sequence = fields.Integer(
        string="Secuencia",
        default=1,
        help="Orden del parámetro en la plantilla (1, 2, 3...)",
    )
    name = fields.Char(
        string="Nombre del Parámetro",
        required=True,
        help="Nombre descriptivo del parámetro",
    )
    template_id = fields.Many2one(
        comodel_name="whatsapp.asertis.template", required=True, ondelete="cascade"
    )
    model = fields.Char(
        related="template_id.model",
        string="Modelo de Origen",
        help="Modelo de Odoo del cual obtener el valor del parámetro",
    )
    field_name = fields.Char(
        string="Campo del Modelo", help="Nombre del campo del modelo a usar"
    )
    format_type = fields.Selection(
        [
            ("text", "Texto"),
            ("number", "Número"),
            ("float", "Decimal"),
            ("currency", "Moneda"),
            ("date", "Fecha"),
            ("datetime", "Fecha y Hora"),
            ("boolean", "Booleano (Sí/No)"),
            ("selection", "Selección"),
        ],
        string="Tipo de Formato",
        default="text",
        required=True,
        help="Formato de salida del valor",
    )
    default_value = fields.Char(
        string="Valor por Defecto", help="Valor a usar si el campo está vacío"
    )

    is_required = fields.Boolean(
        string="Requerido",
        default=False,
        help="Si es obligatorio, no se enviará si está vacío",
    )
    date_format = fields.Selection(
        [
            ("%d/%m/%Y", "DD/MM/YYYY (31/12/2024)"),
            ("%m/%d/%Y", "MM/DD/YYYY (12/31/2024)"),
            ("%Y-%m-%d", "YYYY-MM-DD (2024-12-31)"),
            ("%d-%m-%Y", "DD-MM-YYYY (31-12-2024)"),
            ("%B %d, %Y", "Mes DD, YYYY (Diciembre 31, 2024)"),
            ("%d de %B de %Y", "DD de Mes de YYYY (31 de Diciembre de 2024)"),
        ],
        string="Formato de Fecha",
        default="%d/%m/%Y",
        help="Formato para campos de fecha",
    )

    datetime_format = fields.Selection(
        [
            ("%d/%m/%Y %H:%M", "DD/MM/YYYY HH:MM"),
            ("%d/%m/%Y %I:%M %p", "DD/MM/YYYY HH:MM AM/PM"),
            ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS"),
            ("%d de %B de %Y a las %H:%M", "DD de Mes de YYYY a las HH:MM"),
        ],
        string="Formato de Fecha y Hora",
        default="%d/%m/%Y %H:%M",
        help="Formato para campos de fecha y hora",
    )
    decimal_places = fields.Integer(
        string="Decimales", default=2, help="Número de decimales para números flotantes"
    )
    currency_symbol = fields.Char(
        string="Símbolo de Moneda",
        default="$",
        help="Símbolo a mostrar para valores de moneda",
    )
    boolean_true_text = fields.Char(
        string="Texto para Verdadero",
        default="Sí",
        help="Texto a mostrar cuando el valor booleano es True",
    )
    boolean_false_text = fields.Char(
        string="Texto para Falso",
        default="No",
        help="Texto a mostrar cuando el valor booleano es False",
    )
    field_type = fields.Char(
        string="Tipo de Campo",
        compute="_compute_field_info",
        store=True,
        help="Tipo del campo seleccionado",
    )
    field_string = fields.Char(
        string="Etiqueta del Campo",
        compute="_compute_field_info",
        store=True,
        help="Etiqueta descriptiva del campo",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el parámetro será ignorado",
    )
    notes = fields.Text(string="Notas", help="Notas adicionales sobre este parámetro")

    @api.onchange("model")
    def _get_model_fields(self):
        """Obtener campos disponibles para el modelo seleccionado"""
        result = []
        model_id = self.model
        if not model_id:
            return {"domain": {"field_name": []}}
        try:
            if isinstance(model_id, int):
                model_record = self.sudo().env["ir.model"].browse(model_id)
                if not model_record.exists():
                    return result
                model_name = model_record.model
            elif hasattr(model_id, "model"):
                model_name = model_id
            else:
                return result

            model_obj = self.env[model_name]
            _logger.debug("Obteniendo campos para el modelo: %s", model_obj._name)
            for field_name, field in model_obj._fields.items():
                if self._is_valid_field(field_name, field):
                    display_name = f"{field.string} ({field_name}) - {field.type}"
                    result.append((field_name, display_name))
            result.extend(self._get_related_fields(model_obj))
            result.sort(key=lambda x: x[1])
            _logger.debug(
                "Campos disponibles para modelo %s: %d campos encontrados",
                model_obj._name,
                len(result),
            )
            return {"domain": {"field_name": result}}

        except Exception as e:
            _logger.error("Error obteniendo campos disponibles: %s", str(e))

        return {"domain": {"field_name": result}}

    def _is_valid_field(self, field_name, field):
        """Verificar si un campo es válido para ser usado como parámetro"""
        return (
            not field_name.startswith("_")
            and field.type not in ["one2many", "many2many", "binary"]
            and not (
                getattr(field, "compute", None) and not getattr(field, "store", False)
            )
            and not getattr(field, "readonly", False)
            and field_name
            not in [
                "id",
                "create_uid",
                "create_date",
                "write_uid",
                "write_date",
                "__last_update",
            ]
        )

    def _get_related_fields(self, model):
        """Obtener campos relacionados comunes"""
        related_fields = []
        if "partner_id" in model._fields:
            partner_fields = self._get_partner_fields()
            for field_name, display_name in partner_fields:
                related_fields.append(
                    (f"partner_id.{field_name}", f"Partner: {display_name}")
                )
        if "user_id" in model._fields:
            user_fields = [
                ("user_id.name", "Usuario: Nombre"),
                ("user_id.email", "Usuario: Email"),
                ("user_id.login", "Usuario: Login"),
            ]
            related_fields.extend(user_fields)
        if "company_id" in model._fields:
            company_fields = [
                ("company_id.name", "Compañía: Nombre"),
                ("company_id.email", "Compañía: Email"),
                ("company_id.phone", "Compañía: Teléfono"),
            ]
            related_fields.extend(company_fields)

        return related_fields

    @api.onchange("format_type")
    def _onchange_format_type(self):
        """Configurar valores por defecto según el tipo de formato"""
        if self.format_type == "float" and not self.decimal_places:
            self.decimal_places = 2
        elif self.format_type == "currency":
            if not self.decimal_places:
                self.decimal_places = 2
            if not self.currency_symbol:
                self.currency_symbol = "$"
        elif self.format_type == "date" and not self.date_format:
            self.date_format = "%d/%m/%Y"
        elif self.format_type == "datetime" and not self.datetime_format:
            self.datetime_format = "%d/%m/%Y %H:%M"
        elif self.format_type == "boolean":
            if not self.boolean_true_text:
                self.boolean_true_text = "Sí"
            if not self.boolean_false_text:
                self.boolean_false_text = "No"

    @api.model
    def _get_partner_fields(self):
        """Obtener campos comunes del partner"""
        return [
            ("name", "Nombre - char"),
            ("email", "Email - char"),
            ("phone", "Teléfono - char"),
            ("mobile", "Móvil - char"),
            ("street", "Dirección - char"),
            ("city", "Ciudad - char"),
            ("country_id.name", "País - many2one"),
            ("state_id.name", "Estado - many2one"),
            ("website", "Sitio Web - char"),
            ("vat", "NIT/RUT - char"),
        ]

    @api.depends("model", "field_name")
    def _compute_field_info(self):
        """Obtener información del campo seleccionado"""
        for record in self:
            if not record.model or not record.field_name:
                record.field_type = ""
                record.field_string = ""
                continue

            try:
                model_name = record.model
                model = self.env[model_name]
                if "." in record.field_name:
                    field_path = record.field_name.split(".")
                    current_model = model
                    field_string_parts = []

                    for i, field_part in enumerate(field_path):
                        if field_part in current_model._fields:
                            field = current_model._fields[field_part]
                            field_string_parts.append(field.string)

                            if i < len(field_path) - 1:  # No es el último campo
                                if (
                                    hasattr(field, "comodel_name")
                                    and field.comodel_name
                                ):
                                    current_model = self.env[field.comodel_name]
                                else:
                                    break
                            else:  # Es el último campo
                                record.field_type = field.type
                                record.field_string = " → ".join(field_string_parts)
                                break
                    else:
                        record.field_type = ""
                        record.field_string = ""
                else:
                    if record.field_name in model._fields:
                        field = model._fields[record.field_name]
                        record.field_type = field.type
                        record.field_string = field.string
                    else:
                        record.field_type = ""
                        record.field_string = ""

            except Exception as e:
                _logger.warning(
                    "Error obteniendo info del campo %s: %s", record.field_name, str(e)
                )
                record.field_type = ""
                record.field_string = ""

    @api.onchange("model")
    def _onchange_model(self):
        """Actualizar opciones de field_name cuando cambia model"""
        if self.field_name:
            self.field_name = False
        if not self.model:
            return {"domain": {"field_name": []}}
        try:
            model_obj = self.env[self.model]
            available_fields = []

            # Obtener campos del modelo
            for field_name, field in model_obj._fields.items():
                if self._is_valid_field(field_name, field):
                    display_name = f"{field.string} ({field_name}) - {field.type}"
                    available_fields.append((field_name, display_name))

            # Agregar campos relacionados comunes
            available_fields.extend(self._get_related_fields(model_obj))

            # Ordenar por nombre de campo
            available_fields.sort(key=lambda x: x[1])

            _logger.debug(
                "OnChange model %s: %d campos disponibles",
                self.model,
                len(available_fields),
            )

            # Retornar el dominio actualizado
            return {"domain": {"field_name": available_fields}}

        except Exception as e:
            _logger.error("Error en onchange model_name: %s", str(e))
            return {"domain": {"field_name": []}}

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get para actualizar dinámicamente las opciones de field_name"""
        res = super().fields_get(allfields, attributes)
        if "field_name" in res:
            model_id = self._context.get("default_model_name")
            if model_id and isinstance(model_id, int):
                try:
                    model_record = self.sudo().env["ir.model"].browse(model_id)
                    if model_record.exists():
                        model_obj = self.env[model_record.model]
                        available_fields = []
                        for field_name, field in model_obj._fields.items():
                            if self._is_valid_field(field_name, field):
                                display_name = (
                                    f"{field.string} ({field_name}) - {field.type}"
                                )
                                available_fields.append((field_name, display_name))

                        available_fields.extend(self._get_related_fields(model_obj))
                        available_fields.sort(key=lambda x: x[1])
                        res["field_name"]["selection"] = available_fields

                except Exception as e:
                    _logger.warning("Error en fields_get para field_name: %s", str(e))

        return res

    @api.onchange("field_name")
    def _onchange_field_name(self):
        """Sugerir formato según tipo de campo detectado"""
        if self.field_name and self.model:
            try:
                model = self.env[self.model]
                field_info = None
                if "." in self.field_name:
                    field_path = self.field_name.split(".")
                    current_model = model
                    for i, field_part in enumerate(field_path):
                        if field_part in current_model._fields:
                            field_info = current_model._fields[field_part]
                            if (
                                i < len(field_path) - 1
                                and hasattr(field_info, "comodel_name")
                                and field_info.comodel_name
                            ):
                                current_model = self.env[field_info.comodel_name]
                else:
                    if self.field_name in model._fields:
                        field_info = model._fields[self.field_name]

                if field_info:
                    type_format_map = {
                        "char": "text",
                        "text": "text",
                        "integer": "number",
                        "float": "float",
                        "monetary": "currency",
                        "date": "date",
                        "datetime": "datetime",
                        "boolean": "boolean",
                        "selection": "selection",
                        "many2one": "text",
                    }

                    suggested_format = type_format_map.get(field_info.type, "text")
                    if not self.format_type or self.format_type == "text":
                        self.format_type = suggested_format

            except Exception as e:
                _logger.warning("Error en onchange field_name: %s", str(e))

    @api.constrains("sequence")
    def _check_sequence_positive(self):
        """Validar que la secuencia sea positiva"""
        for record in self:
            if record.sequence <= 0:
                raise ValidationError(_("La secuencia debe ser un número positivo"))

    @api.constrains("decimal_places")
    def _check_decimal_places(self):
        """Validar lugares decimales"""
        for record in self:
            if record.decimal_places < 0 or record.decimal_places > 10:
                raise ValidationError(
                    _("Los lugares decimales deben estar entre 0 y 10")
                )

    def _get_raw_field_value(self, record):
        """Obtener valor crudo del campo, manejando campos relacionados"""
        if "." in self.field_name:
            field_path = self.field_name.split(".")
            current_record = record

            for field_part in field_path:
                if not current_record or not hasattr(current_record, field_part):
                    return None
                current_record = getattr(current_record, field_part, None)

            return current_record
        else:
            return getattr(record, self.field_name, None)

    def _get_source_record(self, record):
        """
        Obtener registro origen según el modelo configurado del parámetro.
        """
        if not self.model:
            return None

        target_model = self.model
        if record._name == target_model:
            return record

        if target_model == "res.partner":
            if hasattr(record, "partner_id") and record.partner_id:
                return record.partner_id

        if target_model == "res.users":
            if hasattr(record, "user_id") and record.user_id:
                return record.user_id

        if target_model == "res.company":
            if hasattr(record, "company_id") and record.company_id:
                return record.company_id

        for field_name, field in record._fields.items():
            if (
                hasattr(field, "comodel_name")
                and field.comodel_name == target_model
                and field.type == "many2one"
            ):

                related_record = getattr(record, field_name, None)
                if related_record:
                    return related_record

        return None

    def _get_fallback_value(self):
        """Obtener valor de respaldo"""
        if self.is_required and not self.default_value:
            raise UserError(_("El parámetro requerido '%s' no tiene valor") % self.name)

        return self.default_value or ""

    def _format_value(self, value):
        """Formatear valor según configuración"""
        if self.format_type == "text":
            return str(value)

        elif self.format_type == "number":
            return str(int(value)) if isinstance(value, (int, float)) else str(value)

        elif self.format_type == "float":
            if isinstance(value, (int, float)):
                return f"{float(value):.{self.decimal_places}f}"
            return str(value)

        elif self.format_type == "currency":
            if isinstance(value, (int, float)):
                formatted = f"{float(value):,.{self.decimal_places}f}"
                return f"{self.currency_symbol}{formatted}"
            return str(value)

        elif self.format_type == "date":
            if isinstance(value, datetime):
                return value.strftime(self.date_format)
            elif hasattr(value, "strftime"):
                return value.strftime(self.date_format)
            return str(value)

        elif self.format_type == "datetime":
            if isinstance(value, datetime):
                return value.strftime(self.datetime_format)
            elif hasattr(value, "strftime"):
                return value.strftime(self.datetime_format)
            return str(value)
        elif self.format_type == "boolean":
            return self.boolean_true_text if value else self.boolean_false_text
        elif self.format_type == "selection":
            try:
                if "." in self.field_name:
                    field_path = self.field_name.split(".")
                    model_name = self.model
                    current_model = self.env[model_name]

                    for field_part in field_path[:-1]:
                        if field_part in current_model._fields:
                            field_obj = current_model._fields[field_part]
                            if (
                                hasattr(field_obj, "comodel_name")
                                and field_obj.comodel_name
                            ):
                                current_model = self.env[field_obj.comodel_name]
                    final_field_name = field_path[-1]
                else:
                    current_model = self.env[self.model]
                    final_field_name = self.field_name
                if final_field_name in current_model._fields:
                    field = current_model._fields[final_field_name]
                    if getattr(field, "type", None) == "selection" and hasattr(
                        field, "selection"
                    ):
                        selection_attr = getattr(field, "selection", None)
                        if callable(selection_attr):
                            selection_values = selection_attr(current_model)
                        else:
                            selection_values = selection_attr

                        if selection_values and isinstance(
                            selection_values, (list, tuple)
                        ):
                            selection_dict = dict(selection_values)
                            return selection_dict.get(value, str(value))
            except Exception as e:
                _logger.warning("Error formateando campo selection: %s", str(e))

            return str(value)

        return str(value)

    def get_field_value(self, record):
        """
        Obtener valor del campo para el registro dado

        Args:
            record: Registro de Odoo del cual extraer el valor

        Returns:
            str: Valor formateado del campo
        """
        self.ensure_one()

        if not self.active:
            return self.default_value or ""

        try:
            source_record = self._get_source_record(record)
            if not source_record:
                return self._get_fallback_value()
            raw_value = self._get_raw_field_value(source_record)

            if (
                raw_value is None
                or raw_value == ""
                or (
                    isinstance(raw_value, bool)
                    and not raw_value
                    and self.field_type != "boolean"
                )
            ):
                return self._get_fallback_value()
            return self._format_value(raw_value)

        except Exception as e:
            _logger.error(
                "Error obteniendo valor del parámetro %s: %s", self.name, str(e)
            )
            return self._get_fallback_value()

    def action_test_parameter(self):
        """Acción para probar el parámetro individualmente"""
        self.ensure_one()

        if not self.model:
            raise UserError(_("El parámetro debe tener un modelo configurado"))
        model = self.env[self.model]
        sample_record = model.search([], limit=1)

        if not sample_record:
            raise UserError(
                _("No hay registros disponibles para probar en el modelo %s")
                % self.model
            )
        try:
            test_value = self.get_field_value(sample_record)
            message = _(
                "Valor de prueba para '%s': %s\nTipo de campo: %s\nRegistro usado: %s"
            ) % (
                self.name,
                test_value,
                self.field_type,
                sample_record.display_name or str(sample_record.id),
            )
            message_type = "success"
        except Exception as e:
            message = _("Error obteniendo valor: %s") % str(e)
            message_type = "danger"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Prueba de Parámetro"),
                "message": message,
                "type": message_type,
                "sticky": True,
            },
        }

    def name_get(self):
        """Nombre personalizado para el parámetro"""
        result = []
        for param in self:
            name = f"#{param.sequence} - {param.name}"
            if param.model:
                name += f" ({param.model})"
            if param.field_name:
                name += f" → {param.field_name}"
            if not param.active:
                name += " [Inactivo]"
            result.append((param.id, name))
        return result
