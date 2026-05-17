from django.db import models


class FiscalTaxationSystem(models.TextChoices):
    OSN = "osn", "ОСН"
    USN_INCOME = "usn_income", "УСН доходы"
    USN_INCOME_OUTCOME = "usn_income_outcome", "УСН доходы-расходы"
    ENVD = "envd", "ЕНВД"
    ESN = "esn", "ЕСХН"
    PATENT = "patent", "Патент"


class FiscalVatCode(models.TextChoices):
    NONE = "none", "Без НДС"
    VAT0 = "vat0", "НДС 0%"
    VAT5 = "vat5", "НДС 5%"
    VAT7 = "vat7", "НДС 7%"
    VAT10 = "vat10", "НДС 10%"
    VAT20 = "vat20", "НДС 20%"
    VAT22 = "vat22", "НДС 22%"
    VAT105 = "vat105", "НДС 5/105"
    VAT107 = "vat107", "НДС 7/107"
    VAT110 = "vat110", "НДС 10/110"
    VAT120 = "vat120", "НДС 20/120"
    VAT122 = "vat122", "НДС 22/122"


class FiscalPaymentSubject(models.TextChoices):
    COMMODITY = "commodity", "Товар"
    SERVICE = "service", "Услуга"
    WORK = "work", "Работа"
    PAYMENT = "payment", "Платеж"


class FiscalPaymentMode(models.TextChoices):
    FULL_PREPAYMENT = "full_prepayment", "Полная предоплата"
    PARTIAL_PREPAYMENT = "partial_prepayment", "Частичная предоплата"
    ADVANCE = "advance", "Аванс"
    FULL_PAYMENT = "full_payment", "Полный расчет"
    PARTIAL_PAYMENT = "partial_payment", "Частичный расчет и кредит"
    CREDIT = "credit", "Передача в кредит"
    CREDIT_PAYMENT = "credit_payment", "Оплата кредита"


class FiscalPaymentType(models.TextChoices):
    CASH = "cash", "Наличные"
    ELECTRONIC = "electronic", "Безналичные/электронные"
    PREPAID = "prepaid", "Предварительная оплата"
    CREDIT = "credit", "Постоплата/кредит"
    OTHER = "other", "Иная форма оплаты"


class FiscalMeasure(models.TextChoices):
    PIECE = "piece", "Штука"
    GRAM = "gram", "Грамм"
    KILOGRAM = "kilogram", "Килограмм"
    TON = "ton", "Тонна"
    CENTIMETER = "centimeter", "Сантиметр"
    DECIMETER = "decimeter", "Дециметр"
    METER = "meter", "Метр"
    SQUARE_METER = "square_meter", "Квадратный метр"
    LITER = "liter", "Литр"
    DAY = "day", "День"
    HOUR = "hour", "Час"
    SERVICE = "service", "Услуга"
