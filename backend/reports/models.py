from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class ReportTemplate(models.Model):
    """Шаблоны отчетов"""

    class ReportType(models.TextChoices):
        FINANCIAL = "financial", "Финансовый отчет"
        SALES = "sales", "Отчет по продажам"
        INVENTORY = "inventory", "Складской отчет"
        PERFORMANCE = "performance", "Отчет по эффективности"
        CUSTOMER = "customer", "Отчет по клиентам"
        TECHNICIAN = "technician", "Отчет по техникам"

    name = models.CharField("Название", max_length=100)
    report_type = models.CharField(
        "Тип отчета", max_length=20, choices=ReportType.choices
    )
    description = models.TextField("Описание", blank=True)

    # Конфигурация отчета
    config = models.JSONField("Конфигурация", default=dict)

    # Права доступа
    required_permissions = models.JSONField("Необходимые права", default=list)
    available_for_roles = models.ManyToManyField(
        "users.Role", blank=True, verbose_name="Доступно для ролей"
    )

    is_active = models.BooleanField("Активен", default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class GeneratedReport(models.Model):
    """Сгенерированные отчеты"""

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    title = models.CharField("Заголовок", max_length=200)

    # Параметры генерации
    parameters = models.JSONField("Параметры", default=dict)
    date_from = models.DateTimeField("С даты")
    date_to = models.DateTimeField("По дату")

    # Данные отчета
    data = models.JSONField("Данные отчета", default=dict)
    summary = models.JSONField("Сводка", default=dict)
    charts_config = models.JSONField("Конфигурация графиков", default=dict)

    # Метаданные
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField("Путь к файлу", max_length=500, blank=True)

    class Meta:
        ordering = ["-generated_at"]


class ReportSchedule(models.Model):
    """Расписание автоматической генерации отчетов"""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Ежедневно"
        WEEKLY = "weekly", "Еженедельно"
        MONTHLY = "monthly", "Ежемесячно"
        QUARTERLY = "quarterly", "Ежеквартально"

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    name = models.CharField("Название", max_length=100)
    frequency = models.CharField("Частота", max_length=20, choices=Frequency.choices)

    # Получатели
    recipients = models.ManyToManyField(User, verbose_name="Получатели")
    email_recipients = models.TextField("Email получатели", blank=True)

    # Параметры
    parameters = models.JSONField("Параметры", default=dict)
    next_run = models.DateTimeField("Следующий запуск")

    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
