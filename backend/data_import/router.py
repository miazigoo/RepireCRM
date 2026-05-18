from typing import Any

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import Field

from shops.models import Shop

from .models import ImportBatch
from .services import ImportRecordInput, create_preflight_batch, import_flow_spec

router = Router(tags=["Импорт данных"])


class ImportRecordSchema(Schema):
    entity_type: str
    external_id: str
    payload: dict[str, Any]
    row_number: int | None = None


class ImportPreflightRequest(Schema):
    source_code: str
    source_name: str = ""
    shop_id: int | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    records: list[ImportRecordSchema]


def _can_import(request) -> bool:
    return (
        request.auth.is_superuser
        or request.auth.is_director
        or request.auth.has_permission("settings.change_shop")
    )


def _serialize_batch(batch: ImportBatch) -> dict:
    issues = [
        {
            "severity": issue.severity,
            "entity_type": issue.entity_type,
            "external_id": issue.external_id,
            "row_number": issue.row_number,
            "field_path": issue.field_path,
            "code": issue.code,
            "message": issue.message,
            "payload": issue.payload,
        }
        for issue in batch.issues.order_by("severity", "row_number", "id")[:300]
    ]
    return {
        "id": batch.id,
        "source": {
            "id": batch.source_id,
            "code": batch.source.code,
            "name": batch.source.name,
        },
        "shop_id": batch.shop_id,
        "status": batch.status,
        "dry_run": batch.dry_run,
        "counters": batch.counters,
        "issues": issues,
    }


@router.get("/flow", response=dict)
def data_import_flow(request):
    """Порядок миграции и шаблоны payload перед dry-run."""
    if not _can_import(request):
        raise PermissionError("Нет прав для подготовки импорта")
    return import_flow_spec()


@router.get("/batches", response=dict)
def list_import_batches(request, limit: int = 20, offset: int = 0):
    if not _can_import(request):
        raise PermissionError("Нет прав для просмотра импорта")
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    query = ImportBatch.objects.select_related("source", "shop").prefetch_related(
        "issues"
    )
    if not request.auth.is_superuser:
        accessible_shop_ids = list(request.auth.shops.values_list("id", flat=True))
        query = query.filter(Q(shop_id__in=accessible_shop_ids) | Q(shop__isnull=True))
    total = query.count()
    batches = query.order_by("-created_at")[offset : offset + limit]
    return {"total": total, "items": [_serialize_batch(batch) for batch in batches]}


@router.post("/preflight", response=dict)
def preflight_import(request, payload: ImportPreflightRequest):
    """Dry-run проверка перед импортом из другой CRM."""
    if not _can_import(request):
        raise PermissionError("Нет прав для подготовки импорта")

    shop = None
    if payload.shop_id:
        shop = get_object_or_404(Shop, id=payload.shop_id)
        if not request.auth.can_access_shop(shop):
            raise PermissionError("Нет доступа к филиалу")

    batch = create_preflight_batch(
        source_code=payload.source_code,
        source_name=payload.source_name or payload.source_code,
        records=[
            ImportRecordInput(
                entity_type=record.entity_type,
                external_id=record.external_id,
                payload=record.payload,
                row_number=record.row_number,
            )
            for record in payload.records
        ],
        created_by=request.auth,
        shop=shop,
        options=payload.options,
    )
    return _serialize_batch(batch)


@router.get("/batches/{import_batch_id}", response=dict)
def get_import_batch(request, import_batch_id: int):
    if not _can_import(request):
        raise PermissionError("Нет прав для просмотра импорта")
    batch = get_object_or_404(
        ImportBatch.objects.select_related("source", "shop").prefetch_related("issues"),
        id=import_batch_id,
    )
    if batch.shop_id and not request.auth.can_access_shop(batch.shop):
        raise PermissionError("Нет доступа к филиалу")
    return _serialize_batch(batch)
