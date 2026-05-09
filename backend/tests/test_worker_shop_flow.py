import json
from datetime import timedelta
from decimal import Decimal

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer, CustomerShopHistory
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from inventory.models import Category, InventoryItem, RetailSale, StockBalance
from orders.models import AdditionalService, Order, OrderService
from shops.models import Shop
from tasks.models import Task
from users.models import Permission, Role

User = get_user_model()


class WorkerShopFlowTestCase(TestCase):
    def setUp(self):
        call_command("init_permissions", verbosity=0)
        self.shop = Shop.objects.create(name="Центр", code="MSK01")
        self.other_shop = Shop.objects.create(name="Север", code="MSK02")
        self.role = Role.objects.get(code=Role.RoleType.MANAGER)
        self.worker = User.objects.create_user(
            username="worker",
            password="pass12345",
            first_name="Анна",
            last_name="Мастер",
            role=self.role,
            current_shop=self.shop,
            compensation_type=User.CompensationType.MIXED,
            fixed_order_payment=Decimal("100"),
            service_commission_percent=Decimal("10"),
            product_commission_percent=Decimal("5"),
        )
        self.worker.shops.add(self.shop, self.other_shop)
        self.customer = Customer.objects.create(
            first_name="Иван", last_name="Клиент", phone="+79990000011"
        )
        CustomerShopHistory.objects.create(customer=self.customer, shop=self.shop)
        CustomerShopHistory.objects.create(customer=self.customer, shop=self.other_shop)
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Смартфон")
        self.model = DeviceModel.objects.create(
            brand=brand, device_type=device_type, name="iPhone 15"
        )

    def auth_headers(self, user=None, shop=None):
        user = user or self.worker
        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str((shop or user.current_shop).id),
        }

    def test_worker_switches_shop_and_created_order_is_bound_to_selected_shop(self):
        switch_response = self.client.post(
            f"/api/auth/switch-shop/{self.other_shop.id}",
            **self.auth_headers(),
        )
        self.assertEqual(switch_response.status_code, 200, switch_response.content)

        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "customer_id": self.customer.id,
                    "device": {"model_id": self.model.id},
                    "problem_description": "Не заряжается",
                    "cost_estimate": 1500,
                    "priority": "normal",
                }
            ),
            content_type="application/json",
            **self.auth_headers(shop=self.other_shop),
        )

        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.shop, self.other_shop)
        self.assertEqual(order.created_by, self.worker)

    def test_orders_are_scoped_to_current_shop_but_customers_are_common(self):
        device = Device.objects.create(model=self.model)
        Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=device,
            problem_description="Shop 1",
            cost_estimate=1000,
            created_by=self.worker,
        )
        Order.objects.create(
            shop=self.other_shop,
            customer=self.customer,
            device=Device.objects.create(model=self.model),
            problem_description="Shop 2",
            cost_estimate=2000,
            created_by=self.worker,
        )

        orders_response = self.client.get(
            "/api/orders/",
            data={"page": 1, "page_size": 100},
            **self.auth_headers(shop=self.shop),
        )
        customers_response = self.client.get(
            "/api/customers/",
            data={"page": 1, "page_size": 100},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(orders_response.status_code, 200, orders_response.content)
        self.assertEqual(orders_response.json()["count"], 1)
        self.assertEqual(
            customers_response.status_code, 200, customers_response.content
        )
        self.assertEqual(customers_response.json()["count"], 1)

    def test_worker_with_permission_can_view_stock_in_unassigned_shop(self):
        external_shop = Shop.objects.create(name="Юг", code="MSK03")
        permission = Permission.objects.get(codename="inventory.view_other_shop_stock")
        self.role.permissions.add(permission)
        category = Category.objects.create(name="Стекла")
        item = InventoryItem.objects.create(
            name="Бронестекло",
            sku="GLASS-1",
            item_type=InventoryItem.ItemType.ACCESSORY,
            category=category,
            purchase_price=100,
            selling_price=500,
            created_by=self.worker,
        )
        balance = StockBalance.objects.get(shop=external_shop, item=item)
        balance.quantity = 7
        balance.save()

        response = self.client.get(
            "/api/inventory/stock-balances",
            data={"shop_id": external_shop.id},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()[0]["shop_id"], external_shop.id)

    def test_employee_report_calculates_service_sales_and_paid_task_salary(self):
        order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=Device.objects.create(model=self.model),
            problem_description="Готов",
            cost_estimate=1000,
            final_cost=2000,
            status=Order.StatusChoices.COMPLETED,
            assigned_to=self.worker,
            created_by=self.worker,
            completed_at=timezone.now(),
        )
        service = AdditionalService.objects.create(
            name="Наклейка стекла",
            category=AdditionalService.ServiceCategory.PROTECTION,
            price=500,
        )
        OrderService.objects.create(order=order, service=service, quantity=1, price=500)
        RetailSale.objects.create(
            shop=self.shop,
            cashier=self.worker,
            status=RetailSale.Status.COMPLETED,
            subtotal=1000,
            total_amount=1000,
            completed_at=timezone.now(),
        )
        Task.objects.create(
            title="Витрина",
            description="Обновить выкладку",
            assignment_type=Task.AssignmentType.INDIVIDUAL,
            assigned_to=self.worker,
            status=Task.Status.COMPLETED,
            is_paid=True,
            payment_amount=300,
            created_by=self.worker,
        )

        response = self.client.get(
            "/api/reports/employees",
            data={"period": "30_days"},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(response.status_code, 200, response.content)
        worker_stats = response.json()["items"][0]
        self.assertEqual(worker_stats["orders"]["completed"], 1)
        self.assertEqual(worker_stats["orders"]["services_revenue"], 500.0)
        self.assertEqual(worker_stats["sales"]["revenue"], 1000.0)
        self.assertEqual(worker_stats["tasks"]["paid_amount"], 300.0)
        self.assertEqual(worker_stats["compensation"]["estimated_salary"], 500.0)

    def test_profile_statistics_uses_current_shop_by_default(self):
        for shop, cost in ((self.shop, 1000), (self.other_shop, 2000)):
            Order.objects.create(
                shop=shop,
                customer=self.customer,
                device=Device.objects.create(model=self.model),
                problem_description=f"Готов {shop.code}",
                cost_estimate=cost,
                final_cost=cost,
                status=Order.StatusChoices.COMPLETED,
                assigned_to=self.worker,
                created_by=self.worker,
                completed_at=timezone.now(),
            )

        scoped_response = self.client.get(
            "/api/auth/profile/statistics",
            data={"period": "30_days"},
            **self.auth_headers(shop=self.shop),
        )
        all_shops_response = self.client.get(
            "/api/auth/profile/statistics",
            data={"period": "30_days", "all_shops": True},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(scoped_response.status_code, 200, scoped_response.content)
        self.assertEqual(scoped_response.json()["orders"]["completed"], 1)
        self.assertEqual(scoped_response.json()["orders"]["repair_revenue"], 1000.0)
        self.assertEqual(
            all_shops_response.status_code, 200, all_shops_response.content
        )
        self.assertEqual(all_shops_response.json()["orders"]["completed"], 2)

    def test_order_creation_rejects_service_from_another_shop(self):
        service = AdditionalService.objects.create(
            name="Пленка только Север",
            category=AdditionalService.ServiceCategory.PROTECTION,
            price=700,
        )
        service.shops.add(self.other_shop)

        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "customer_id": self.customer.id,
                    "device": {"model_id": self.model.id},
                    "problem_description": "Проверка услуг",
                    "cost_estimate": 1500,
                    "priority": "normal",
                    "additional_services": [{"service_id": service.id, "quantity": 1}],
                }
            ),
            content_type="application/json",
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("недоступна", response.json()["error"])
        self.assertFalse(OrderService.objects.filter(service=service).exists())

    def test_service_catalog_management_can_show_inactive_services(self):
        inactive = AdditionalService.objects.create(
            name="Старая услуга",
            category=AdditionalService.ServiceCategory.OTHER,
            price=100,
            is_active=False,
        )

        default_response = self.client.get(
            "/api/orders/additional-services",
            **self.auth_headers(shop=self.shop),
        )
        management_response = self.client.get(
            "/api/orders/additional-services",
            data={"include_inactive": True},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(default_response.status_code, 200, default_response.content)
        self.assertNotIn(inactive.id, [item["id"] for item in default_response.json()])
        self.assertEqual(
            management_response.status_code, 200, management_response.content
        )
        self.assertIn(inactive.id, [item["id"] for item in management_response.json()])

    def test_order_assignment_requires_worker_shop_access(self):
        external_worker = User.objects.create_user(
            username="external-worker",
            password="pass12345",
            first_name="Петр",
            last_name="Север",
            role=self.role,
            current_shop=self.other_shop,
        )
        external_worker.shops.add(self.other_shop)
        order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=Device.objects.create(model=self.model),
            problem_description="Назначение",
            cost_estimate=1000,
            created_by=self.worker,
        )

        response = self.client.put(
            f"/api/orders/{order.id}",
            data=json.dumps({"assigned_to_id": external_worker.id}),
            content_type="application/json",
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(response.status_code, 400, response.content)
        order.refresh_from_db()
        self.assertIsNone(order.assigned_to)

    def test_tasks_list_is_scoped_to_current_shop_by_default(self):
        Task.objects.create(
            title="Задача Центр",
            description="Только текущий филиал",
            assignment_type=Task.AssignmentType.SHOP,
            assigned_shop=self.shop,
            created_by=self.worker,
        )
        Task.objects.create(
            title="Задача Север",
            description="Другой филиал",
            assignment_type=Task.AssignmentType.SHOP,
            assigned_shop=self.other_shop,
            created_by=self.worker,
        )

        scoped_response = self.client.get(
            "/api/tasks/",
            data={"page": 1, "page_size": 100},
            **self.auth_headers(shop=self.shop),
        )
        all_shops_response = self.client.get(
            "/api/tasks/",
            data={"page": 1, "page_size": 100, "all_shops": True},
            **self.auth_headers(shop=self.shop),
        )

        self.assertEqual(scoped_response.status_code, 200, scoped_response.content)
        self.assertEqual(scoped_response.json()["count"], 1)
        self.assertEqual(scoped_response.json()["items"][0]["title"], "Задача Центр")
        self.assertEqual(
            all_shops_response.status_code, 200, all_shops_response.content
        )
        self.assertEqual(all_shops_response.json()["count"], 2)
