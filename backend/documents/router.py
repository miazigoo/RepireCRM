from typing import Optional

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from ninja import Router

from .models import RetailDocument
from .receipt_service import create_retail_pdf_and_store, send_retail_receipt_email

router = Router(tags=["Документы"])


@router.post("/retail-sales/{sale_id}/receipt/pdf", response=dict)
def generate_sale_pdf(request, sale_id: int, doc_type: str = "retail_invoice"):
    """
    doc_type: retail_invoice | retail_receipt
    """
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав")
    from inventory.models import RetailSale

    sale = get_object_or_404(RetailSale, id=sale_id)
    doc = create_retail_pdf_and_store(sale, doc_type)
    return {"success": True, "document_id": doc.id, "url": doc.file.url}


@router.get("/retail-sales/{sale_id}/receipt/download")
def download_sale_pdf(request, sale_id: int, doc_type: str = "retail_invoice"):
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав")
    from inventory.models import RetailSale

    sale = get_object_or_404(RetailSale, id=sale_id)
    doc = (
        RetailDocument.objects.filter(sale=sale, document_type=doc_type)
        .order_by("-generated_at")
        .first()
    )
    if not doc:
        doc = create_retail_pdf_and_store(sale, doc_type)
    doc.file.open("rb")
    resp = FileResponse(
        doc.file, as_attachment=True, filename=doc.file.name.split("/")[-1]
    )
    return resp


@router.post("/retail-sales/{sale_id}/receipt/email", response=dict)
def email_sale_pdf(
    request,
    sale_id: int,
    to_email: Optional[str] = None,
    doc_type: str = "retail_invoice",
):
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав")
    from inventory.models import RetailSale

    sale = get_object_or_404(RetailSale, id=sale_id)
    # email адрес: из запроса, или из клиента продажи при наличии
    email = to_email or (
        sale.customer.email if sale.customer and sale.customer.email else None
    )
    if not email:
        return {"success": False, "error": "Не указан email получателя"}
    doc = (
        RetailDocument.objects.filter(sale=sale, document_type=doc_type)
        .order_by("-generated_at")
        .first()
    )
    if not doc:
        doc = create_retail_pdf_and_store(sale, doc_type)
    ok = send_retail_receipt_email(email, sale, doc)
    return {"success": bool(ok)}
