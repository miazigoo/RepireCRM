from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from customers.models import Customer
from data_import.models import ExternalRecordLink, ImportIssue, MigrationSource
from data_import.services import (
    ImportRecordInput,
    create_preflight_batch,
    import_flow_spec,
)
from shops.models import Shop

User = get_user_model()


class DataImportPreflightTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Main", code="MAIN")
        self.user = User.objects.create_user(
            username="owner",
            password="pass12345",
            current_shop=self.shop,
            is_director=True,
        )
        self.user.shops.add(self.shop)

    def test_preflight_collects_duplicates_and_missing_fields(self):
        batch = create_preflight_batch(
            source_code="legacy-crm",
            source_name="Legacy CRM",
            shop=self.shop,
            created_by=self.user,
            records=[
                ImportRecordInput(
                    entity_type="customer",
                    external_id="C-1",
                    payload={"phone": "+79991234567"},
                    row_number=1,
                ),
                ImportRecordInput(
                    entity_type="customer",
                    external_id="C-1",
                    payload={},
                    row_number=2,
                ),
            ],
        )

        self.assertEqual(batch.status, "failed")
        self.assertEqual(batch.counters["records"], 2)
        self.assertEqual(batch.counters["errors"], 2)
        self.assertTrue(
            ImportIssue.objects.filter(batch=batch, code="duplicate_in_batch").exists()
        )
        self.assertTrue(
            ImportIssue.objects.filter(
                batch=batch,
                code="missing_required_field",
                field_path="phone",
            ).exists()
        )

    def test_preflight_warns_when_external_record_already_linked(self):
        source = MigrationSource.objects.create(
            code="legacy-crm",
            name="Legacy CRM",
        )
        customer = Customer.objects.create(
            first_name="Ivan",
            last_name="Ivanov",
            phone="+79991234567",
        )
        ExternalRecordLink.objects.create(
            source=source,
            entity_type="customer",
            external_id="C-1",
            content_type=ContentType.objects.get_for_model(Customer),
            object_id=customer.id,
            checksum="old",
        )

        batch = create_preflight_batch(
            source_code="legacy-crm",
            source_name="Legacy CRM",
            shop=self.shop,
            created_by=self.user,
            records=[
                ImportRecordInput(
                    entity_type="customer",
                    external_id="C-1",
                    payload={"phone": "+79991234567"},
                    row_number=1,
                )
            ],
        )

        self.assertEqual(batch.status, "ready")
        self.assertEqual(batch.counters["warnings"], 1)
        self.assertTrue(
            ImportIssue.objects.filter(batch=batch, code="already_imported").exists()
        )

    def test_import_flow_spec_documents_order_and_templates(self):
        spec = import_flow_spec()

        self.assertEqual(
            spec["entity_order"],
            ["customer", "device", "inventory_item", "order", "payment"],
        )
        templates = {
            template["entity_type"]: template for template in spec["templates"]
        }
        self.assertIn("phone", templates["customer"]["required_fields"])
        self.assertIn("shop_code", templates["order"]["required_fields"])
        self.assertEqual(templates["payment"]["sample"]["amount"], 250000)
