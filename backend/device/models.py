from django.db import models


class DeviceBrand(models.Model):
    """Бренды устройств"""
    name = models.CharField("Название", max_length=50, unique=True)
    logo = models.ImageField("Логотип", upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        db_table = 'device_brands'
        verbose_name = 'Бренд устройства'
        verbose_name_plural = 'Бренды устройств'
        ordering = ['name']

    def __str__(self):
        return self.name


class DeviceType(models.Model):
    """Типы устройств"""
    name = models.CharField("Название", max_length=50, unique=True)
    icon = models.CharField("Иконка", max_length=50, blank=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        db_table = 'device_types'
        verbose_name = 'Тип устройства'
        verbose_name_plural = 'Типы устройств'
        ordering = ['name']

    def __str__(self):
        return self.name


class DeviceModel(models.Model):
    """Модели устройств"""
    brand = models.ForeignKey(
        DeviceBrand,
        on_delete=models.CASCADE,
        verbose_name="Бренд"
    )
    device_type = models.ForeignKey(
        DeviceType,
        on_delete=models.CASCADE,
        verbose_name="Тип устройства"
    )
    name = models.CharField("Название модели", max_length=100)
    model_number = models.CharField("Номер модели", max_length=50, blank=True)
    release_year = models.PositiveIntegerField("Год выпуска", null=True, blank=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        db_table = 'device_models'
        verbose_name = 'Модель устройства'
        verbose_name_plural = 'Модели устройств'
        unique_together = ['brand', 'name']
        ordering = ['brand__name', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class Device(models.Model):
    """Конкретное устройство клиента"""
    model = models.ForeignKey(
        DeviceModel,
        on_delete=models.PROTECT,
        verbose_name="Модель"
    )
    serial_number = models.CharField("Серийный номер", max_length=100, blank=True)
    imei = models.CharField("IMEI", max_length=20, blank=True)
    color = models.CharField("Цвет", max_length=50, blank=True)
    storage_capacity = models.CharField("Объем памяти", max_length=20, blank=True)

    # Дополнительные характеристики (JSON поле для гибкости)
    specifications = models.JSONField("Характеристики", default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'devices'
        verbose_name = 'Устройство'
        verbose_name_plural = 'Устройства'

    def __str__(self):
        parts = [str(self.model)]
        if self.color:
            parts.append(self.color)
        if self.storage_capacity:
            parts.append(self.storage_capacity)
        return ' '.join(parts)