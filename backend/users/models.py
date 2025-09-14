from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Role(models.Model):
    """Роли пользователей"""

    class RoleType(models.TextChoices):
        DIRECTOR = 'director', 'Директор'
        MANAGER = 'manager', 'Менеджер'
        TECHNICIAN = 'technician', 'Техник'
        CASHIER = 'cashier', 'Кассир'
        ADMIN = 'admin', 'Администратор'

    name = models.CharField("Название", max_length=50, unique=True)
    code = models.CharField(
        "Код роли",
        max_length=20,
        choices=RoleType.choices,
        unique=True
    )
    description = models.TextField("Описание", blank=True)
    permissions = models.ManyToManyField(
        'Permission',
        blank=True,
        verbose_name="Разрешения"
    )

    class Meta:
        db_table = 'roles'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class Permission(models.Model):
    """Разрешения"""

    class PermissionCategory(models.TextChoices):
        ORDERS = 'orders', 'Заказы'
        CUSTOMERS = 'customers', 'Клиенты'
        INVENTORY = 'inventory', 'Склад'
        REPORTS = 'reports', 'Отчеты'
        SETTINGS = 'settings', 'Настройки'
        USERS = 'users', 'Пользователи'

    name = models.CharField("Название", max_length=100)
    codename = models.CharField("Кодовое имя", max_length=100, unique=True)
    category = models.CharField(
        "Категория",
        max_length=20,
        choices=PermissionCategory.choices
    )
    description = models.TextField("Описание", blank=True)

    class Meta:
        db_table = 'permissions'
        verbose_name = 'Разрешение'
        verbose_name_plural = 'Разрешения'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class User(AbstractUser):
    """Кастомная модель пользователя"""
    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    middle_name = models.CharField("Отчество", max_length=50, blank=True)

    phone = PhoneNumberField("Телефон", blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Роль"
    )

    # Привязка к магазинам
    shops = models.ManyToManyField(
        'shops.Shop',
        through='UserShop',
        verbose_name="Магазины",
        blank=True
    )
    current_shop = models.ForeignKey(
        'shops.Shop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_users',
        verbose_name="Текущий магазин"
    )

    # Дополнительные поля
    avatar = models.ImageField(
        "Аватар",
        upload_to='avatars/',
        blank=True,
        null=True
    )
    is_director = models.BooleanField("Директор", default=False)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_shop = models.ForeignKey(
        'shops.Shop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_login_users',
        verbose_name="Последний магазин входа"
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name(self):
        """Полное имя пользователя"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    def get_available_shops(self):
        """Получить доступные магазины для пользователя"""
        if self.is_director:
            return self.shops.filter(is_active=True)
        return self.shops.filter(is_active=True)

    def has_permission(self, permission_codename: str) -> bool:
        """Проверка наличия разрешения у пользователя"""
        if self.is_superuser:
            return True

        if not self.role:
            return False

        return self.role.permissions.filter(
            codename=permission_codename
        ).exists()

    def can_access_shop(self, shop) -> bool:
        """Может ли пользователь получить доступ к магазину"""
        if self.is_superuser or self.is_director:
            return True
        return self.shops.filter(id=shop.id).exists()


class UserShop(models.Model):
    """Промежуточная модель для связи пользователя с магазинами"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE)
    is_manager = models.BooleanField("Менеджер магазина", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_shops'
        unique_together = ['user', 'shop']
        verbose_name = 'Пользователь-Магазин'
        verbose_name_plural = 'Пользователи-Магазины'
