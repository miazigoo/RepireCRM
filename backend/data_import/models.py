from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class MigrationSource(models.Model):
    """Внешняя CRM/таблица/файл, из которого импортируются данные."""

    code = models.CharField("Код источника", max_length=80, unique=True)
    name = models.CharField("Название", max_length=160)
    system_type = models.CharField("Тип CRM", max_length=80, blank=True)
    notes = models.TextField("Заметки", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Источник импорта"
        verbose_name_plural = "Источники импорта"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ImportBatch(models.Model):
    """Один прогон импорта или dry-run проверки."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        VALIDATING = "validating", "Проверяется"
        READY = "ready", "Готов к импорту"
        IMPORTING = "importing", "Импортируется"
        COMPLETED = "completed", "Завершен"
        FAILED = "failed", "Ошибка"

    source = models.ForeignKey(
        MigrationSource, on_delete=models.PROTECT, related_name="batches"
    )
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.PROTECT, null=True, blank=True
    )
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    dry_run = models.BooleanField("Только проверка", default=True)
    options = models.JSONField("Опции", default=dict, blank=True)
    counters = models.JSONField("Счетчики", default=dict, blank=True)
    error_message = models.TextField("Ошибка", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Пакет импорта"
        verbose_name_plural = "Пакеты импорта"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "status"]),
            models.Index(fields=["shop", "created_at"]),
        ]

    def __str__(self):
        return f"{self.source.code} #{self.id}"


class StagedImportRecord(models.Model):
    """Строка/объект до фактического создания бизнес-сущности."""

    class Status(models.TextChoices):
        NEW = "new", "Новый"
        VALID = "valid", "Валиден"
        WARNING = "warning", "Есть предупреждения"
        ERROR = "error", "Ошибка"
        IMPORTED = "imported", "Импортирован"
        SKIPPED = "skipped", "Пропущен"

    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="records"
    )
    entity_type = models.CharField("Тип сущности", max_length=80)
    external_id = models.CharField("Внешний ID", max_length=160)
    row_number = models.PositiveIntegerField("Номер строки", null=True, blank=True)
    payload = models.JSONField("Исходные данные", default=dict, blank=True)
    checksum = models.CharField("Checksum", max_length=64, blank=True)
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.NEW
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Строка импорта"
        verbose_name_plural = "Строки импорта"
        ordering = ["row_number", "id"]
        indexes = [
            models.Index(fields=["batch", "entity_type", "status"]),
            models.Index(fields=["entity_type", "external_id"]),
        ]


class ExternalRecordLink(models.Model):
    """Идемпотентная связь внешнего ID с объектом CRM."""

    source = models.ForeignKey(
        MigrationSource, on_delete=models.CASCADE, related_name="record_links"
    )
    entity_type = models.CharField("Тип сущности", max_length=80)
    external_id = models.CharField("Внешний ID", max_length=160)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    checksum = models.CharField("Checksum", max_length=64, blank=True)
    raw_snapshot = models.JSONField("Снимок исходных данных", default=dict, blank=True)
    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="record_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Связь внешней записи"
        verbose_name_plural = "Связи внешних записей"
        unique_together = ["source", "entity_type", "external_id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["entity_type", "external_id"]),
        ]


class ImportIssue(models.Model):
    """Ошибка или предупреждение preflight/import проверки."""

    class Severity(models.TextChoices):
        ERROR = "error", "Ошибка"
        WARNING = "warning", "Предупреждение"
        INFO = "info", "Информация"

    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="issues"
    )
    record = models.ForeignKey(
        StagedImportRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="issues",
    )
    severity = models.CharField(
        "Важность", max_length=20, choices=Severity.choices, default=Severity.ERROR
    )
    entity_type = models.CharField("Тип сущности", max_length=80, blank=True)
    external_id = models.CharField("Внешний ID", max_length=160, blank=True)
    row_number = models.PositiveIntegerField("Номер строки", null=True, blank=True)
    field_path = models.CharField("Поле", max_length=160, blank=True)
    code = models.CharField("Код", max_length=80)
    message = models.TextField("Сообщение")
    payload = models.JSONField("Контекст", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Проблема импорта"
        verbose_name_plural = "Проблемы импорта"
        ordering = ["severity", "row_number", "id"]
        indexes = [
            models.Index(fields=["batch", "severity"]),
            models.Index(fields=["entity_type", "external_id"]),
        ]
