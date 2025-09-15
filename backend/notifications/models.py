
from django.db import models
from django.contrib.auth import get_user_model
from shops.models import Shop

User = get_user_model()


class NotificationType(models.Model):
    """Типы уведомлений"""
    name = models.CharField("Название", max_length=50, unique=True)
    code = models.CharField("Код", max_length=50, unique=True)
    description = models.TextField("Описание", blank=True)
    icon = models.CharField("Иконка", max_length=50, default="notifications")
    color = models.CharField("Цвет", max_length=20, default="primary")
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        db_table = 'notification_types'
        verbose_name = 'Тип уведомления'
        verbose_name_plural = 'Типы уведомлений'

    def __str__(self):
        return self.name


class Notification(models.Model):
    """Уведомления"""

    class Priority(models.TextChoices):
        LOW = 'low', 'Низкий'
        NORMAL = 'normal', 'Обычный'
        HIGH = 'high', 'Высокий'
        URGENT = 'urgent', 'Срочный'

    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        verbose_name="Тип уведомления"
    )
    title = models.CharField("Заголовок", max_length=200)
    message = models.TextField("Сообщение")
    priority = models.CharField(
        "Приоритет",
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )

    # Получатели
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Получатель"
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Магазин",
        help_text="Если указан, уведомление получат все пользователи магазина"
    )
    role_code = models.CharField(
        "Код роли",
        max_length=50,
        blank=True,
        help_text="Если указан, уведомление получат пользователи с этой ролью"
    )

    # Связанные объекты
    related_object_type = models.CharField("Тип объекта", max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField("ID объекта", null=True, blank=True)

    # Метаданные
    data = models.JSONField("Дополнительные данные", default=dict, blank=True)
    action_url = models.CharField("Ссылка для действия", max_length=500, blank=True)

    # Статус
    is_read = models.BooleanField("Прочитано", default=False)
    is_sent = models.BooleanField("Отправлено", default=False)
    sent_at = models.DateTimeField("Время отправки", null=True, blank=True)
    read_at = models.DateTimeField("Время прочтения", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_notifications',
        verbose_name="Создал"
    )

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['shop', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient or 'Всем'}"


class NotificationSettings(models.Model):
    """Настройки уведомлений пользователя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )

    # Способы доставки
    email_enabled = models.BooleanField("Email уведомления", default=True)
    browser_enabled = models.BooleanField("Браузерные уведомления", default=True)
    sound_enabled = models.BooleanField("Звуковые уведомления", default=True)

    # Типы уведомлений
    order_status_changes = models.BooleanField("Изменения статуса заказов", default=True)
    new_orders = models.BooleanField("Новые заказы", default=True)
    customer_messages = models.BooleanField("Сообщения от клиентов", default=True)
    system_alerts = models.BooleanField("Системные оповещения", default=True)
    loyalty_updates = models.BooleanField("Обновления программы лояльности", default=True)

    # Время работы
    quiet_hours_start = models.TimeField("Начало тихих часов", null=True, blank=True)
    quiet_hours_end = models.TimeField("Конец тихих часов", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_settings'
        verbose_name = 'Настройки уведомлений'
        verbose_name_plural = 'Настройки уведомлений'

    def __str__(self):
        return f"Настройки уведомлений - {self.user.username}"
