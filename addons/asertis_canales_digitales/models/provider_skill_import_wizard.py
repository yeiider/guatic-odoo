from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import pandas as pd
import logging
from .utils.retry import retry_on_transient_error

_logger = logging.getLogger(__name__)


class ProviderSkillImportWizard(models.TransientModel):
    _name = "provider.skill.import.wizard"
    _description = "Importador de habilidades desde Excel"

    file = fields.Binary(string="Archivo Excel", required=True)
    file_name = fields.Char(string="Nombre del archivo")
    result = fields.Text(string="Resultado", readonly=True)

    def action_download_template(self):
        """Generar y devolver la plantilla para crear habilidades masivamente"""
        providers = self.env["chat.provider"].sudo().search([("is_active", "=", True)])

        data = {
            "name": ["Ejemplo de Habilidad"],
            "code": ["DATA_ANALYSIS"],
            "description": [
                "Capacidad para analizar y procesar conjuntos de datos complejos"
            ],
            "priority": [10],
            "provider": ["OpenAI"],
        }

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Habilidades", index=False)
            if providers:
                providers_df = pd.DataFrame(
                    {
                        "Proveedores Disponibles": [p.name for p in providers],
                        "Descripción": ["Proveedor activo" for _ in providers],
                    }
                )
                providers_df.to_excel(
                    writer, sheet_name="Proveedores_Disponibles", index=False
                )

            instructions_df = pd.DataFrame(
                {
                    "Campo": ["name", "code", "description", "priority", "provider"],
                    "Descripción": [
                        "Nombre de la habilidad (REQUERIDO)",
                        "Código único de la habilidad (OPCIONAL)",
                        "Descripción detallada de la habilidad (OPCIONAL)",
                        "Prioridad numérica (1-10, por defecto: 10)",
                        "Nombre del proveedor (REQUERIDO - debe coincidir con lista)",
                    ],
                    "Ejemplo": [
                        "Análisis de datos",
                        "DATA_ANALYSIS",
                        "Capacidad para analizar conjuntos de datos",
                        "10",
                        "OpenAI",
                    ],
                }
            )
            instructions_df.to_excel(writer, sheet_name="Instrucciones", index=False)

        output.seek(0)
        excel_bytes = output.getvalue()
        encoded_file = base64.b64encode(excel_bytes).decode("utf-8")
        self.file_name = "plantilla_habilidades.xlsx"
        self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("name", "=", "plantilla_habilidades.xlsx"),
            ]
        ).unlink()
        self.file = encoded_file
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": self.file_name,
                    "type": "binary",
                    "datas": encoded_file,
                    "res_model": self._name,
                    "res_id": self.id,
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "public": False,
                }
            )
        )
        download_url = f"/web/content/{attachment.id}?download=true"

        return {
            "type": "ir.actions.act_url",
            "url": download_url,
            "target": "self",
        }

    @retry_on_transient_error(max_retries=3, initial_delay=0.1)
    def action_import_file(self):
        if not self.file:
            raise UserError("Debes subir un archivo Excel primero.")

        # Validar archivo Excel
        try:
            file_data = base64.b64decode(self.file)
            xls = pd.ExcelFile(io.BytesIO(file_data))
            if "Habilidades" not in xls.sheet_names:
                raise UserError(
                    "La hoja 'Habilidades' no se encuentra en el archivo. Asegúrate de no cambiar el nombre."
                )
            df = xls.parse("Habilidades")
        except Exception as e:
            raise UserError(f"Error al leer el archivo: {e}")

        # Validar columnas requeridas
        required_columns = ["name", "provider"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise UserError(
                f"Faltan las siguientes columnas requeridas: {', '.join(missing_columns)}"
            )

        # Procesar importación
        return self._process_import(df)

    def _process_import(self, df):
        """Procesar la importación de datos"""
        total = len(df)
        creadas = 0
        errores = []

        # Procesar cada fila
        for i, row in df.iterrows():
            try:
                # Validar campo 'name'
                if pd.isna(row.get("name")) or not str(row.get("name")).strip():
                    errores.append(f"[Fila {i+2}] El campo 'name' es requerido.")
                    continue

                # Validar campo 'provider'
                if pd.isna(row.get("provider")) or not str(row.get("provider")).strip():
                    errores.append(f"[Fila {i+2}] El campo 'provider' es requerido.")
                    continue

                provider_name = str(row["provider"]).strip()
                provider = (
                    self.env["chat.provider"]
                    .sudo()
                    .search(
                        [("name", "=", provider_name), ("is_active", "=", True)],
                        limit=1,
                    )
                )
                if not provider:
                    errores.append(
                        f"[Fila {i+2}] Proveedor '{provider_name}' no encontrado."
                    )
                    continue

                skill_name = str(row["name"]).strip()

                # Verificar si ya existe
                existing = (
                    self.env["provider.skill"]
                    .sudo()
                    .search(
                        [("name", "=", skill_name), ("provider_id", "=", provider.id)],
                        limit=1,
                    )
                )

                if existing:
                    errores.append(
                        f"[Fila {i+2}] Habilidad '{skill_name}' ya existe para el proveedor '{provider.name}'."
                    )
                    continue

                # Preparar datos de la habilidad
                skill_data = {
                    "name": skill_name,
                    "provider_id": provider.id,
                    "description": "",
                    "priority": 10,
                }

                if not pd.isna(row.get("code")) and str(row.get("code")).strip():
                    skill_data["code"] = str(row["code"]).strip()

                if (
                    not pd.isna(row.get("description"))
                    and str(row.get("description")).strip()
                ):
                    skill_data["description"] = str(row["description"]).strip()

                if not pd.isna(row.get("priority")):
                    try:
                        prioridad = int(row["priority"])
                        if 1 <= prioridad <= 10:
                            skill_data["priority"] = prioridad
                    except (ValueError, TypeError):
                        pass

                # Crear la habilidad
                self.env["provider.skill"].sudo().create(skill_data)
                creadas += 1

            except Exception as e:
                _logger.info(f"Error al procesar fila {i+2}: {e}")

        # Preparar resumen
        resumen = (
            f"Total filas: {total}\nCreadas: {creadas}\nErrores: {len(errores)}\n\n"
        )
        if errores:
            resumen += "Errores encontrados:\n" + "\n".join(errores[:10])
            if len(errores) > 10:
                resumen += f"\n... y {len(errores) - 10} errores más."

        # Actualizar el resultado usando el método seguro
        return self._update_result_safely(resumen)

    @retry_on_transient_error(max_retries=3, initial_delay=0.1)
    def _update_result_safely(self, resumen):
        """Actualizar el resultado de forma segura"""
        try:
            # Intentar actualizar el campo result
            self.write({"result": resumen})

            return {
                "type": "ir.actions.act_window",
                "res_model": "provider.skill.import.wizard",
                "view_mode": "form",
                "res_id": self.id,
                "target": "new",
            }
        except Exception as e:
            # Si falla la escritura, mostrar resultado con UserError
            self.result = resumen
            raise UserError(f"Importación completada:\n{resumen}")

    def write(self, vals):
        """Sobrescribir write para mejor manejo de errores"""
        try:
            return super(ProviderSkillImportWizard, self).write(vals)
        except Exception as e:
            # Log del error y re-raise para que el decorador lo maneje
            import logging

            _logger = logging.getLogger(__name__)
            _logger.error(f"Error en write: {e}")
            raise
