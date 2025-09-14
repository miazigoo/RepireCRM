from django.db import models

class Part(models.Model):
    name = models.CharField("Название", max_length=100)
    sku = models.CharField("Артикул", max_length=50, unique=True)
    quantity = models.PositiveIntegerField("Количество")
    min_quantity = models.PositiveIntegerField("Минимальное количество")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True)
