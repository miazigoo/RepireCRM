from django.db import models

from orders.models import Order


class Document(models.Model):
    class DocumentType(models.TextChoices):
        RECEIPT = 'receipt', 'Квитанция'
        WARRANTY = 'warranty', 'Гарантийный талон'
        INVOICE = 'invoice', 'Счет'
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to='documents/')
    generated_at = models.DateTimeField(auto_now_add=True)
