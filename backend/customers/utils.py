import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


def normalize_phone(raw: str) -> str:
    try:
        # По умолчанию RU, можно вынести в настройки
        p = phonenumbers.parse(raw, "RU")
        if not phonenumbers.is_valid_number(p):
            return raw
        return phonenumbers.format_number(p, PhoneNumberFormat.E164)
    except NumberParseException:
        return raw
