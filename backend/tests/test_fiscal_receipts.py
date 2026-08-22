from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from finance.fiscal_constants import FiscalPaymentType, FiscalVatCode
from finance.fiscal_receipts import (
    create_or_update_payment_receipt,
    receipt_snapshot_to_tbank,
    receipt_snapshot_to_yookassa,
)
from finance.models import Payment, PaymentMethod
from inventory.models import Category, InventoryItem, RetailSale, RetailSaleItem
from orders.models import AdditionalService, Order, OrderService
from shops.models import Organization, Shop, ShopSettings

User = get_user_model()


class FiscalReceiptTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Main", code="MAIN", currency="RUB")
        self.organization = Organization.objects.create(name="Main Org")
        self.settings = ShopSettings.objects.create(
            shop=self.shop,
            organization=self.organization,
            fiscalization_enabled=True,
            default_goods_vat_code=FiscalVatCode.VAT22,
            default_service_vat_code=FiscalVatCode.NONE,
        )
        self.user = User.objects.create_user(
            username="cashier",
            password="pass12345",
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.cash = PaymentMethod.objects.create(
            name="Наличные",
            code="cash",
            is_cash=True,
            fiscal_payment_type=FiscalPaymentType.CASH,
        )
        self.card = PaymentMethod.objects.create(
            name="Карта",
            code="card",
            is_cash=False,
            fiscal_payment_type=FiscalPaymentType.ELECTRONIC,
        )
        self.customer = Customer.objects.create(
            first_name="Ivan",
            last_name="Ivanov",
            phone="+79991234567",
            email="ivan@example.test",
        )
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Смартфон")
        model = DeviceModel.objects.create(
            brand=brand,
            device_type=device_type,
            name="iPhone 15",
        )
        self.device = Device.objects.create(model=model)

    def create_order(self, *, prepayment=Decimal("0")):
        return Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Не включается",
            cost_estimate=Decimal("5000"),
            prepayment=prepayment,
            created_by=self.user,
        )

    def test_full_order_payment_builds_itemized_provider_receipt(self):
        order = self.create_order()
        service = AdditionalService.objects.create(
            name="Защитное стекло",
            category=AdditionalService.ServiceCategory.ACCESSORIES,
            price=Decimal("1000"),
        )
        OrderService.objects.create(
            order=order,
            service=service,
            quantity=1,
            price=Decimal("1000"),
        )
        payment = Payment.objects.create(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            amount=Decimal("6000"),
            payment_method=self.card,
            order=order,
            payment_date=timezone.now(),
            created_by=self.user,
        )

        receipt = create_or_update_payment_receipt(payment)

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.total_amount, Decimal("6000.00"))
        self.assertEqual(receipt.received_amount, Decimal("6000.00"))
        self.assertEqual(receipt.items.count(), 2)
        payload = receipt_snapshot_to_yookassa(receipt.normalized_snapshot)
        self.assertEqual(payload["tax_system_code"], 2)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["payment_subject"], "service")

    def test_final_order_payment_tracks_prepaid_offset_for_local_kkm(self):
        order = self.create_order(prepayment=Decimal("1000"))
        payment = Payment.objects.create(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            amount=Decimal("4000"),
            payment_method=self.card,
            order=order,
            payment_date=timezone.now(),
            created_by=self.user,
        )

        receipt = create_or_update_payment_receipt(payment)

        self.assertEqual(receipt.total_amount, Decimal("5000.00"))
        self.assertEqual(receipt.received_amount, Decimal("4000.00"))
        self.assertEqual(
            receipt.normalized_snapshot["payments"],
            [
                {"type": "electronic", "amount": "4000.00"},
                {"type": "prepaid", "amount": "1000.00"},
            ],
        )
        with self.assertRaisesMessage(ValueError, "must match the charged amount"):
            receipt_snapshot_to_yookassa(receipt.normalized_snapshot)

    def test_retail_sale_receipt_uses_goods_vat(self):
        category = Category.objects.create(name="Запчасти")
        item = InventoryItem.objects.create(
            name="Аккумулятор",
            sku="BAT-1",
            item_type=InventoryItem.ItemType.COMPONENT,
            category=category,
            purchase_price=Decimal("1000"),
            selling_price=Decimal("2500"),
            created_by=self.user,
        )
        sale = RetailSale.objects.create(
            shop=self.shop,
            cashier=self.user,
            customer=self.customer,
            subtotal=Decimal("2500"),
            total_amount=Decimal("2500"),
        )
        RetailSaleItem.objects.create(
            sale=sale,
            item=item,
            quantity=1,
            unit_price=Decimal("2500"),
            total_price=Decimal("2500"),
        )
        payment = Payment.objects.create(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            amount=Decimal("2500"),
            payment_method=self.cash,
            retail_sale=sale,
            payment_date=timezone.now(),
            created_by=self.user,
        )

        receipt = create_or_update_payment_receipt(payment)
        tbank_payload = receipt_snapshot_to_tbank(receipt.normalized_snapshot)

        self.assertEqual(receipt.items.get().vat_code, FiscalVatCode.VAT22)
        self.assertEqual(tbank_payload["Items"][0]["PaymentObject"], "commodity")
        self.assertEqual(tbank_payload["Items"][0]["Tax"], "vat22")


class FiscalReceiptValueErrorRegressionTests(TestCase):
    """
    Regression: ValueError raised by build_payment_receipt_snapshot must NOT roll back the
    surrounding @transaction.atomic and must NOT silently drop the payment record.
    Instead a FAILED PaymentReceipt should be persisted.
    """

    def setUp(self):
        self.shop = Shop.objects.create(name="TestShop", code="TST", currency="RUB")
        self.organization = Organization.objects.create(name="Test Org")
        ShopSettings.objects.create(
            shop=self.shop,
            organization=self.organization,
            fiscalization_enabled=True,
            default_goods_vat_code=FiscalVatCode.VAT22,
            default_service_vat_code=FiscalVatCode.NONE,
        )
        self.user = User.objects.create_user(
            username="fiscal-tester",
            password="pass12345",
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.cash = PaymentMethod.objects.create(
            name="Наличные2",
            code="cash2",
            is_cash=True,
            fiscal_payment_type=FiscalPaymentType.CASH,
        )

    def test_payment_with_no_customer_contact_creates_failed_receipt(self):
        """
        Trigger: payment linked to order whose customer has no email/phone.
        build_payment_receipt_snapshot raises ValueError("Для онлайн-чека нужен email или телефон клиента").
        The outer @transaction.atomic must NOT roll back; a FAILED PaymentReceipt is persisted.
        """
        from customers.models import Customer
        from device.models import Device, DeviceBrand, DeviceModel, DeviceType
        from orders.models import Order

        brand = DeviceBrand.objects.create(name="Brand")
        dtype = DeviceType.objects.create(name="Type")
        dmodel = DeviceModel.objects.create(name="Model", brand=brand, device_type=dtype)
        device = Device.objects.create(
            model=dmodel,
            serial_number="SN001",
        )
        customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            phone="",
            email="",
        )
        order = Order.objects.create(
            shop=self.shop,
            customer=customer,
            device=device,
            cost_estimate=Decimal("0.00"),
            created_by=self.user,
        )
        payment = Payment.objects.create(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            amount=Decimal("1000"),
            payment_method=self.cash,
            order=order,
            payment_date=timezone.now(),
            created_by=self.user,
        )

        receipt = create_or_update_payment_receipt(payment)

        self.assertIsNotNone(receipt, "PaymentReceipt must be created even when snapshot fails")
        from finance.models import PaymentReceipt
        self.assertEqual(receipt.status, PaymentReceipt.Status.FAILED)
        self.assertNotEqual(receipt.error_message, "")
