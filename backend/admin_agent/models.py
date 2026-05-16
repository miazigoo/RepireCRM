from django.db import models


class AdminServiceState(models.Model):
    """Persisted state received from the central RepireCRM Admin service."""

    DEFAULT_KEY = "default"

    key = models.CharField(max_length=40, unique=True, default=DEFAULT_KEY)
    subscription = models.JSONField(default=dict, blank=True)
    campaigns = models.JSONField(default=list, blank=True)
    support_unread = models.PositiveIntegerField(default=0)
    server_time = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_service_state"
        verbose_name = "Состояние RepireCRM Admin"
        verbose_name_plural = "Состояния RepireCRM Admin"

    def __str__(self):
        return f"RepireCRM Admin state: {self.key}"

    @classmethod
    def get_solo(cls):
        state, _ = cls.objects.get_or_create(key=cls.DEFAULT_KEY)
        return state
