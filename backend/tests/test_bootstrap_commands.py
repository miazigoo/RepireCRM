from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from analytics.models import RevenueSnapshot
from customers.models import Customer
from finance.models import Expense, Payment
from inventory.models import (
    InventoryItem,
    InventoryProductGroup,
    PurchaseOrder,
    PurchaseRequest,
    PurchaseRequestBatch,
    StockBalance,
)
from orders.models import Order
from users.models import Permission, Role


class BootstrapCommandsTestCase(TestCase):
    def test_init_permissions_creates_api_settings_permissions_and_admin_role(self):
        call_command("init_permissions", verbosity=0)

        self.assertTrue(
            Permission.objects.filter(codename="settings.view_shop").exists()
        )
        self.assertTrue(
            Permission.objects.filter(codename="settings.change_shop").exists()
        )
        self.assertTrue(
            Permission.objects.filter(codename="reports.view_dashboard").exists()
        )
        self.assertTrue(
            Permission.objects.filter(codename="inventory.view_stock").exists()
        )
        admin_role = Role.objects.get(code=Role.RoleType.ADMIN)
        self.assertTrue(
            admin_role.permissions.filter(codename="settings.view_shop").exists()
        )
        self.assertTrue(
            admin_role.permissions.filter(codename="settings.change_shop").exists()
        )
        self.assertTrue(
            admin_role.permissions.filter(codename="reports.view_dashboard").exists()
        )
        self.assertTrue(
            admin_role.permissions.filter(codename="inventory.view_stock").exists()
        )

    def test_init_permissions_adds_missing_permissions_to_existing_default_role(self):
        role = Role.objects.create(name="Администратор", code=Role.RoleType.ADMIN)

        call_command("init_permissions", verbosity=0)

        role.refresh_from_db()
        self.assertTrue(role.permissions.filter(codename="settings.view_shop").exists())
        self.assertTrue(
            role.permissions.filter(codename="settings.change_shop").exists()
        )
        self.assertTrue(
            role.permissions.filter(codename="reports.view_dashboard").exists()
        )
        self.assertTrue(
            role.permissions.filter(codename="inventory.view_stock").exists()
        )

    def test_create_test_data_builds_demo_dataset(self):
        call_command(
            "create_test_data",
            reset_demo=True,
            months=2,
            orders=8,
            customers=6,
            stdout=StringIO(),
            verbosity=0,
        )

        self.assertEqual(
            Order.objects.filter(
                notes__startswith="[demo]",
                is_warranty_case=False,
            ).count(),
            8,
        )
        self.assertTrue(
            Order.objects.filter(
                notes__startswith="[demo][warranty]",
                is_warranty_case=True,
                warranty_parent__isnull=False,
            ).exists()
        )
        self.assertEqual(Customer.objects.filter(phone__startswith="+7908").count(), 6)
        self.assertTrue(
            Payment.objects.filter(description__startswith="[demo]").exists()
        )
        self.assertTrue(
            Expense.objects.filter(invoice_number__startswith="DEMO-").exists()
        )
        self.assertTrue(
            PurchaseOrder.objects.filter(notes__startswith="[demo]").exists()
        )
        self.assertTrue(
            InventoryProductGroup.objects.filter(
                description__startswith="[demo]"
            ).exists()
        )
        self.assertTrue(
            InventoryItem.objects.filter(
                sku__startswith="DEMO-",
                procurement_group__isnull=False,
            ).exists()
        )
        self.assertTrue(
            PurchaseRequest.objects.filter(
                notes__startswith="[demo-procurement]"
            ).exists()
        )
        self.assertTrue(
            PurchaseRequestBatch.objects.filter(
                purchase_request__notes__startswith="[demo-procurement]"
            ).exists()
        )
        self.assertTrue(
            PurchaseRequest.objects.filter(
                notes__startswith="[demo-procurement]",
                status__in=[
                    PurchaseRequest.Status.SUBMITTED,
                    PurchaseRequest.Status.SPLIT,
                    PurchaseRequest.Status.PARTIALLY_RECEIVED,
                ],
            ).exists()
        )
        self.assertTrue(
            StockBalance.objects.filter(shop__code__in=["MSK01", "SPB01"]).exists()
        )
        self.assertTrue(RevenueSnapshot.objects.exists())
