import logging
import phonenumbers
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException

_logger = logging.getLogger(__name__)


class ContactFormatter:
    """Utility class for formatting and normalizing contact information."""

    @staticmethod
    def normalize_phone_number(number_str):
        """
        Formatea un número de teléfono a un formato internacional estándar,
        intentando detectar la región automáticamente.
        """
        if not isinstance(number_str, str):
            return number_str

        try:
            parsed_number = phonenumbers.parse(number_str, None)

            if phonenumbers.is_valid_number(parsed_number):
                formatter = PhoneNumberFormat.INTERNATIONAL
                return phonenumbers.format_number(parsed_number, formatter)
            else:
                return "".join(filter(str.isdigit, number_str))

        except NumberParseException:
            return "".join(filter(str.isdigit, number_str))
        except Exception:
            _logger.error(f"Error inesperado al formatear {number_str}")
            return number_str

    @staticmethod
    def get_phone_search_variants(phone):
        """Generate phone number variants for comprehensive search."""
        if not phone:
            return []

        variants = set()
        variants.add(phone)  # Número original

        # Solo dígitos
        digits_only = "".join(filter(str.isdigit, phone))
        if digits_only and len(digits_only) >= 7:
            variants.add(digits_only)

        # Limpiar caracteres especiales ANTES del procesamiento phonenumbers
        clean_phone = (
            phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )
        if clean_phone != phone:
            variants.add(clean_phone)

        # Usar phonenumbers para obtener formatos estándar
        phone_to_parse = clean_phone if clean_phone else phone

        try:
            # Intentar parsear sin región específica
            parsed_number = phonenumbers.parse(phone_to_parse, None)
            if phonenumbers.is_valid_number(parsed_number):
                # Formato internacional: +57 317 345 9847
                international = phonenumbers.format_number(
                    parsed_number, PhoneNumberFormat.INTERNATIONAL
                )
                variants.add(international)

                # Formato nacional: (317) 345-9847
                national = phonenumbers.format_number(
                    parsed_number, PhoneNumberFormat.NATIONAL
                )
                variants.add(national)

                # Formato E164: +573173459847
                e164 = phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)
                variants.add(e164)

                # Solo el número nacional: 3173459847
                national_number = str(parsed_number.national_number)
                variants.add(national_number)

            else:
                # Si no es válido, intentar con región Colombia
                raise NumberParseException(
                    NumberParseException.INVALID_COUNTRY_CODE, "Fallback to CO region"
                )

        except NumberParseException:
            try:
                # Fallback: intentar con región Colombia
                parsed_number = phonenumbers.parse(phone_to_parse, "CO")
                if phonenumbers.is_valid_number(parsed_number):
                    international = phonenumbers.format_number(
                        parsed_number, PhoneNumberFormat.INTERNATIONAL
                    )
                    variants.add(international)

                    national = phonenumbers.format_number(
                        parsed_number, PhoneNumberFormat.NATIONAL
                    )
                    variants.add(national)

                    e164 = phonenumbers.format_number(
                        parsed_number, PhoneNumberFormat.E164
                    )
                    variants.add(e164)

                    national_number = str(parsed_number.national_number)
                    variants.add(national_number)
            except NumberParseException:
                # Último fallback: usar normalize_phone_number
                normalized = ContactFormatter.normalize_phone_number(phone)
                if normalized and normalized != phone:
                    variants.add(normalized)
        except Exception as e:
            _logger.error(f"Error inesperado al formatear {phone}: {e}")

        # Agregar variantes con y sin "+" (solo si no existen ya)
        variants_copy = list(variants)
        for variant in variants_copy:
            if variant.startswith("+"):
                without_plus = variant[1:]
                if without_plus:
                    variants.add(without_plus)
            else:
                with_plus = "+" + variant
                variants.add(with_plus)

        # Filtrar variantes válidas (>= 7 dígitos) y convertir a lista sin duplicados
        valid_variants = []
        for variant in variants:
            digit_count = sum(1 for c in variant if c.isdigit())
            if digit_count >= 7 and variant not in valid_variants:
                valid_variants.append(variant)

        _logger.info(f"Phone variants for '{phone}': {valid_variants}")
        return valid_variants


class PartnerSearchCriteria:
    """Utility class for building search domains for res.partner."""

    @staticmethod
    def _create_or_conditions(conditions):
        """
        Crea condiciones OR correctamente para dominios de Odoo.
        Para N condiciones, necesitamos N-1 operadores '|' al inicio.
        """
        if not conditions:
            return []
        if len(conditions) == 1:
            return conditions

        # Para N condiciones, necesitamos N-1 operadores '|' al inicio
        result = ["|"] * (len(conditions) - 1)
        result.extend(conditions)
        return result

    @classmethod
    def build_contact_search_domain(cls, contact_metadata):
        """Build search domain from contact metadata (phone/email)."""

        # Construir condiciones para teléfono
        phone_conditions = []
        if contact_metadata.phone_number:
            phone_variants = ContactFormatter.get_phone_search_variants(
                contact_metadata.phone_number.strip()
            )

            for variant in phone_variants:
                # Para cada variante, agregar condición exacta e ILIKE
                phone_conditions.append(("mobile", "=", variant))
                phone_conditions.append(("mobile", "ilike", f"%{variant}%"))

        # Construir condiciones para email
        email_conditions = []
        if contact_metadata.email:
            email_conditions.append(("email", "=", contact_metadata.email))

        # Combinar todas las condiciones de contacto (phone + email)
        all_contact_conditions = phone_conditions + email_conditions

        # Si no hay condiciones de contacto, solo filtrar por is_company
        if not all_contact_conditions:
            return [("is_company", "=", False)]

        # Crear dominio con OR para todas las condiciones de contacto
        contact_domain = cls._create_or_conditions(all_contact_conditions)

        # Combinar con is_company usando AND
        # El dominio final es: is_company=False AND (todas las condiciones de contacto)
        final_domain =  ["&", ("is_company", "=", False)] + contact_domain

        _logger.info("Final search domain: %s", final_domain)
        return final_domain
