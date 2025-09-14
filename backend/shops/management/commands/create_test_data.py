from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shops.models import Shop, ShopSettings
from users.models import Role, Permission
from devices.models import DeviceBrand, DeviceType, DeviceModel
from orders.models import AdditionalService
from customers.models import Customer

User = get_user_model()


class Command(BaseCommand):
    help = 'Создание тестовых данных для разработки'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Создание тестовых данных...')

        # Создаем магазины
        shop1 = Shop.objects.get_or_create(
            code='MSK01',
            defaults={
                'name': 'Ремонт+ Москва Центр',
                'address': 'г. Москва, ул. Тверская, д. 1',
                'phone': '+7 (495) 123-45-67',
                'email': 'moscow@repair-plus.ru'
            }
        )[0]

        shop2 = Shop.objects.get_or_create(
            code='SPB01',
            defaults={
                'name': 'Ремонт+ СПб Невский',
                'address': 'г. Санкт-Петербург, Невский пр., д. 100',
                'phone': '+7 (812) 987-65-43',
                'email': 'spb@repair-plus.ru'
            }
        )[0]

        # Создаем настройки магазинов
        ShopSettings.objects.get_or_create(
            shop=shop1,
            defaults={
                'order_number_prefix': 'MSK',
                'work_hours_start': '09:00',
                'work_hours_end': '21:00'
            }
        )

        # Создаем роли и разрешения
        self.call_command('init_permissions')

        # Создаем пользователей
        director = User.objects.get_or_create(
            username='director',
            defaults={
                'first_name': 'Иван',
                'last_name': 'Директоров',
                'email': 'director@repair-plus.ru',
                'is_director': True,
                'role': Role.objects.get(code='director')
            }
        )[0]
        director.set_password('director123')
        director.save()
        director.shops.set([shop1, shop2])
        director.current_shop = shop1
        director.save()

        manager = User.objects.get_or_create(
            username='manager',
            defaults={
                'first_name': 'Анна',
                'last_name': 'Менеджерова',
                'email': 'manager@repair-plus.ru',
                'role': Role.objects.get(code='manager')
            }
        )[0]
        manager.set_password('manager123')
        manager.save()
        manager.shops.set([shop1])
        manager.current_shop = shop1
        manager.save()

        # Создаем бренды и типы устройств
        apple = DeviceBrand.objects.get_or_create(name='Apple')[0]
        samsung = DeviceBrand.objects.get_or_create(name='Samsung')[0]
        xiaomi = DeviceBrand.objects.get_or_create(name='Xiaomi')[0]

        phone_type = DeviceType.objects.get_or_create(
            name='Смартфон', defaults={'icon': 'phone'}
        )[0]
        tablet_type = DeviceType.objects.get_or_create(
            name='Планшет', defaults={'icon': 'tablet'}
        )[0]

        # Создаем модели устройств
        DeviceModel.objects.get_or_create(
            brand=apple, device_type=phone_type, name='iPhone 15 Pro',
            defaults={'model_number': 'A3101', 'release_year': 2023}
        )
        DeviceModel.objects.get_or_create(
            brand=samsung, device_type=phone_type, name='Galaxy S24',
            defaults={'model_number': 'SM-S921B', 'release_year': 2024}
        )

        # Создаем дополнительные услуги
        AdditionalService.objects.get_or_create(
            name='Защитное стекло',
            defaults={
                'category': 'protection',
                'description': 'Наклейка защитного стекла на экран',
                'price': 500.00
            }
        )
        AdditionalService.objects.get_or_create(
            name='Чехол',
            defaults={
                'category': 'accessories',
                'description': 'Продажа защитного чехла',
                'price': 1500.00
            }
        )

        # Создаем тестовых клиентов
        Customer.objects.get_or_create(
            phone='+79161234567',
            defaults={
                'first_name': 'Петр',
                'last_name': 'Петров',
                'email': 'petrov@example.com',
                'source': 'website',
                'created_by': manager
            }
        )

        self.stdout.write(
            self.style.SUCCESS('✅ Тестовые данные успешно созданы!')
        )
        self.stdout.write('👤 Пользователи:')
        self.stdout.write('   Директор: director / director123')
        self.stdout.write('   Менеджер: manager / manager123')