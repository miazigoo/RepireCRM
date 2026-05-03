from django.core.management import call_command
from django.test import TestCase

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
