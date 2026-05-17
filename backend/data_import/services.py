from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import (
    ExternalRecordLink,
    ImportBatch,
    ImportIssue,
    MigrationSource,
    StagedImportRecord,
)

ENTITY_REQUIRED_FIELDS = {
    "customer": {"external_id", "phone"},
    "device": {"external_id", "customer_external_id", "model"},
    "order": {"external_id", "customer_external_id", "shop_code", "created_at"},
    "inventory_item": {"external_id", "name", "sku"},
    "payment": {"external_id", "amount", "payment_date"},
}

ENTITY_ORDER = {
    "customer": 10,
    "device": 20,
    "inventory_item": 30,
    "order": 40,
    "payment": 50,
}


@dataclass(frozen=True)
class ImportRecordInput:
    entity_type: str
    external_id: str
    payload: dict[str, Any]
    row_number: int | None = None


def normalize_external_id(value: Any) -> str:
    normalized = str(value or "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized[:160]


def normalize_entity_type(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")[:80]


def payload_checksum(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _issue(
    *,
    batch: ImportBatch,
    record: StagedImportRecord | None,
    severity: str,
    code: str,
    message: str,
    field_path: str = "",
    payload: dict[str, Any] | None = None,
):
    ImportIssue.objects.create(
        batch=batch,
        record=record,
        severity=severity,
        entity_type=record.entity_type if record else "",
        external_id=record.external_id if record else "",
        row_number=record.row_number if record else None,
        field_path=field_path,
        code=code,
        message=message,
        payload=payload or {},
    )


def _record_status(record: StagedImportRecord) -> str:
    severities = set(record.issues.values_list("severity", flat=True))
    if ImportIssue.Severity.ERROR in severities:
        return StagedImportRecord.Status.ERROR
    if ImportIssue.Severity.WARNING in severities:
        return StagedImportRecord.Status.WARNING
    return StagedImportRecord.Status.VALID


@transaction.atomic
def create_preflight_batch(
    *,
    source_code: str,
    source_name: str,
    records: list[ImportRecordInput],
    created_by=None,
    shop=None,
    options: dict[str, Any] | None = None,
) -> ImportBatch:
    source, _ = MigrationSource.objects.get_or_create(
        code=normalize_external_id(source_code),
        defaults={
            "name": source_name or source_code,
            "system_type": options.get("system_type", "") if options else "",
        },
    )
    batch = ImportBatch.objects.create(
        source=source,
        shop=shop,
        status=ImportBatch.Status.VALIDATING,
        dry_run=True,
        options=options or {},
        created_by=created_by,
        started_at=timezone.now(),
    )

    seen: set[tuple[str, str]] = set()
    staged: list[StagedImportRecord] = []
    for raw in records:
        entity_type = normalize_entity_type(raw.entity_type)
        external_id = normalize_external_id(raw.external_id)
        payload = raw.payload or {}
        record = StagedImportRecord.objects.create(
            batch=batch,
            entity_type=entity_type,
            external_id=external_id,
            row_number=raw.row_number,
            payload=payload,
            checksum=payload_checksum(payload),
        )
        staged.append(record)

        key = (entity_type, external_id)
        if not entity_type:
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.ERROR,
                code="missing_entity_type",
                message="Не указан тип сущности",
                field_path="entity_type",
            )
        if not external_id:
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.ERROR,
                code="missing_external_id",
                message="Не указан внешний ID",
                field_path="external_id",
            )
        if key in seen:
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.ERROR,
                code="duplicate_in_batch",
                message="Дублирующийся внешний ID внутри одного пакета",
            )
        seen.add(key)

        required = ENTITY_REQUIRED_FIELDS.get(entity_type, {"external_id"})
        missing = sorted(
            field
            for field in required
            if field != "external_id" and payload.get(field) in (None, "")
        )
        for field in missing:
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.ERROR,
                code="missing_required_field",
                message=f"Не заполнено обязательное поле: {field}",
                field_path=field,
            )

        if entity_type not in ENTITY_REQUIRED_FIELDS:
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.WARNING,
                code="unknown_entity_type",
                message="Неизвестный тип сущности; импорт потребует явного маппера",
            )

        if (
            external_id
            and ExternalRecordLink.objects.filter(
                source=source,
                entity_type=entity_type,
                external_id=external_id,
            ).exists()
        ):
            _issue(
                batch=batch,
                record=record,
                severity=ImportIssue.Severity.WARNING,
                code="already_imported",
                message=(
                    "Запись уже связана с объектом CRM "
                    "и будет обновляться идемпотентно"
                ),
            )

    for record in staged:
        record.status = _record_status(record)
        record.save(update_fields=["status"])

    counters = {
        "records": len(staged),
        "valid": StagedImportRecord.objects.filter(
            batch=batch, status=StagedImportRecord.Status.VALID
        ).count(),
        "warnings": ImportIssue.objects.filter(
            batch=batch, severity=ImportIssue.Severity.WARNING
        ).count(),
        "errors": ImportIssue.objects.filter(
            batch=batch, severity=ImportIssue.Severity.ERROR
        ).count(),
        "by_entity": {},
    }
    for entity_type in sorted(
        set(
            StagedImportRecord.objects.filter(batch=batch).values_list(
                "entity_type", flat=True
            )
        ),
        key=lambda item: ENTITY_ORDER.get(item, 999),
    ):
        counters["by_entity"][entity_type] = StagedImportRecord.objects.filter(
            batch=batch, entity_type=entity_type
        ).count()

    batch.counters = counters
    batch.status = (
        ImportBatch.Status.READY
        if counters["errors"] == 0
        else ImportBatch.Status.FAILED
    )
    batch.completed_at = timezone.now()
    batch.save(update_fields=["counters", "status", "completed_at"])
    return batch
