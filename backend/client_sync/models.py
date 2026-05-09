from __future__ import annotations

from django.db import models


class ClientPortalIntegration(models.Model):
    """Настройки внешнего клиентского backend для одной компании."""

    class AuthPolicy(models.TextChoices):
        PHONE_OR_EMAIL = "phone_or_email", "Телефон или email"
        PHONE_ONLY = "phone_only", "Только телефон"
        EMAIL_ONLY = "email_only", "Только email"

    organization = models.OneToOneField(
        "shops.Organization",
        on_delete=models.CASCADE,
        related_name="client_portal_integration",
        verbose_name="Организация",
    )
    enabled = models.BooleanField("Клиентская часть включена", default=False)
    base_url = models.URLField("URL клиентского backend", blank=True)
    api_key = models.CharField("Sync API ключ", max_length=255, blank=True)
    tenant_key = models.CharField(
        "Ключ tenant/company",
        max_length=80,
        blank=True,
        help_text="Стабильный код компании во внешнем клиентском backend",
    )
    client_domain = models.URLField("Домен клиентского кабинета", blank=True)
    auth_policy = models.CharField(
        "Политика входа клиентов",
        max_length=20,
        choices=AuthPolicy.choices,
        default=AuthPolicy.PHONE_OR_EMAIL,
    )
    support_phone = models.CharField("Телефон поддержки", max_length=40, blank=True)
    support_email = models.EmailField("Email поддержки", blank=True)
    brand_name = models.CharField("Название бренда", max_length=120, blank=True)
    accent_color = models.CharField("Акцентный цвет", max_length=20, blank=True)
    portal_banner_enabled = models.BooleanField(
        "Показывать рекламный баннер в клиентском кабинете",
        default=False,
    )
    portal_banner_title = models.CharField(
        "Заголовок баннера",
        max_length=200,
        blank=True,
    )
    portal_banner_subtitle = models.CharField(
        "Подзаголовок баннера",
        max_length=500,
        blank=True,
    )
    portal_banner_image_url = models.URLField(
        "Картинка баннера (URL)",
        blank=True,
    )
    portal_banner_link_url = models.URLField(
        "Ссылка при клике на баннер",
        blank=True,
    )
    last_push_at = models.DateTimeField("Последний push заказов", null=True, blank=True)
    last_pull_at = models.DateTimeField(
        "Последний pull действий", null=True, blank=True
    )
    last_error = models.TextField("Последняя ошибка", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_portal_integrations"
        verbose_name = "Интеграция клиентского кабинета"
        verbose_name_plural = "Интеграции клиентских кабинетов"
        indexes = [
            models.Index(fields=["enabled"]),
            models.Index(fields=["tenant_key"]),
        ]

    def __str__(self):
        return f"{self.organization}: {'on' if self.enabled else 'off'}"

    @property
    def is_configured(self):
        return bool(self.enabled and self.base_url and self.api_key)


class ClientSyncOrderState(models.Model):
    """Состояние отправки конкретного заказа во внешний клиентский backend."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SYNCED = "synced", "Синхронизирован"
        ERROR = "error", "Ошибка"

    integration = models.ForeignKey(
        ClientPortalIntegration,
        on_delete=models.CASCADE,
        related_name="order_states",
        verbose_name="Интеграция",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="client_sync_states",
        verbose_name="Заказ",
    )
    remote_order_id = models.CharField(
        "ID заказа в кабинете", max_length=120, blank=True
    )
    payload_hash = models.CharField("Hash последнего снимка", max_length=64, blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempts = models.PositiveIntegerField("Попытки", default=0)
    last_error = models.TextField("Последняя ошибка", blank=True)
    last_synced_at = models.DateTimeField(
        "Последняя успешная синхронизация", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_sync_order_states"
        verbose_name = "Состояние синхронизации заказа"
        verbose_name_plural = "Состояния синхронизации заказов"
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "order"],
                name="uniq_client_sync_order_state",
            )
        ]
        indexes = [
            models.Index(fields=["integration", "status"]),
            models.Index(fields=["order"]),
            models.Index(fields=["last_synced_at"]),
        ]

    def __str__(self):
        return f"{self.order_id}: {self.status}"


class ClientSyncAction(models.Model):
    """Действие клиента, полученное из внешнего кабинета и применяемое в CRM."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Получено"
        APPLIED = "applied", "Применено"
        REJECTED = "rejected", "Отклонено"
        ERROR = "error", "Ошибка"

    integration = models.ForeignKey(
        ClientPortalIntegration,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="Интеграция",
    )
    external_id = models.CharField("ID действия во внешнем кабинете", max_length=120)
    action_type = models.CharField("Тип действия", max_length=80)
    payload = models.JSONField("Payload", default=dict, blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    related_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_sync_actions",
        verbose_name="Связанный заказ",
    )
    related_task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_sync_actions",
        verbose_name="Связанная задача",
    )
    error_message = models.TextField("Ошибка", blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField("Применено", null=True, blank=True)
    synced_back_at = models.DateTimeField(
        "Ответ отправлен в кабинет", null=True, blank=True
    )

    class Meta:
        db_table = "client_sync_actions"
        verbose_name = "Действие клиентского кабинета"
        verbose_name_plural = "Действия клиентского кабинета"
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "external_id"],
                name="uniq_client_sync_action",
            )
        ]
        indexes = [
            models.Index(fields=["integration", "status"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["related_order"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self):
        return f"{self.external_id}: {self.action_type}"
