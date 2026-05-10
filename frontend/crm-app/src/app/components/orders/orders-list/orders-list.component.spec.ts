import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Order } from '../../../core/models/models';
import { OrdersService } from '../../../services/orders.service';
import { OrdersListComponent } from './orders-list.component';

describe('OrdersListComponent', () => {
  let fixture: ComponentFixture<OrdersListComponent>;
  let component: OrdersListComponent;
  let ordersService: jasmine.SpyObj<OrdersService>;

  const order = {
    id: 2,
    order_number: 'ORD-SPB01-000002',
    status: 'received',
    priority: 'urgent',
    problem_description: 'Не включается',
    cost_estimate: 900,
    total_cost: 900,
    prepayment: 0,
    remaining_payment: 900,
    created_at: '2026-05-05T20:32:00Z',
    updated_at: '2026-05-05T20:32:00Z',
    additional_services: [],
    customer: {
      id: 1,
      first_name: 'Петр',
      last_name: 'Петров',
      phone: '+79161234567',
      orders_count: 3,
      total_spent: 3300,
      marketing_consent: true,
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T10:00:00Z',
    },
    device: {
      id: 1,
      color: 'Черный',
      storage_capacity: '128 ГБ',
      serial_number: 'SN123456',
      imei: '356789012345678',
      model: {
        id: 1,
        name: 'iPhone 13',
        brand: { id: 1, name: 'Apple' },
        device_type: { id: 1, name: 'Смартфон' },
      },
    },
    device_condition: 'Следы эксплуатации на корпусе',
    accessories: 'Коробка и кабель',
  } as Order;

  beforeEach(async () => {
    ordersService = jasmine.createSpyObj<OrdersService>('OrdersService', ['getOrdersPage']);
    ordersService.getOrdersPage.and.returnValue(of({
      items: [order],
      count: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    }));

    await TestBed.configureTestingModule({
      imports: [OrdersListComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: OrdersService, useValue: ordersService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OrdersListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders the redesigned orders registry without legacy cards or RUB text', () => {
    const text = normalizeText(fixture.nativeElement);
    const headerCells = fixture.nativeElement.querySelectorAll(
      '.mat-mdc-header-cell',
    ) as NodeListOf<HTMLElement>;
    const headers = Array.from(headerCells).map(cell => normalizeText(cell));

    expect(text).toContain('Сервисная очередь');
    expect(text).toContain('Рабочий список');
    expect(text).toContain('ORD-SPB01-000002');
    expect(text).toContain('900 ₽');
    expect(text).not.toContain('RUB');
    expect(headers).toEqual(['Заказ', 'Клиент', 'Устройство', 'Статус', 'Приоритет']);
    expect(headers).not.toContain('Финансы');
    expect(headers).not.toContain('Создан');
    expect(headers).not.toContain('Действия');
    expect(fixture.nativeElement.querySelector('.orders-page')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('mat-card')).toBeFalsy();
  });

  it('expands a row with device details and card actions', () => {
    expect(fixture.nativeElement.querySelector('.order-device-detail')).toBeFalsy();

    const row = fixture.nativeElement.querySelector('.order-data-row') as HTMLElement;
    row.click();
    fixture.detectChanges();

    const detail = fixture.nativeElement.querySelector('.order-device-detail') as HTMLElement;
    const text = normalizeText(detail);

    expect(detail).toBeTruthy();
    expect(text).toContain('Устройство в заказе');
    expect(text).toContain('Apple iPhone 13');
    expect(text).toContain('Не включается');
    expect(text).toContain('Тип');
    expect(text).toContain('Смартфон');
    expect(text).toContain('Серийный номер');
    expect(text).toContain('SN123456');
    expect(text).toContain('Карточка заказа');
    expect(text).toContain('Редактировать');
  });

  it('exposes operational metrics from the loaded orders', () => {
    expect(component.totalOrders).toBe(1);
    expect(component.activeOrders).toBe(1);
    expect(component.urgentOrders).toBe(1);
    expect(component.pipelineValue).toBe(900);
  });

  it('loads the first server page instead of fetching a full client-side list', () => {
    expect(ordersService.getOrdersPage).toHaveBeenCalledOnceWith(1, 20, {});
    expect(component.loadedOrders).toBe(1);
  });

  it('renders suspicious order text as text, not executable HTML', () => {
    component.dataSource.data = [{
      ...order,
      problem_description: '<img src=x onerror=alert(1)>Не включается',
    }];
    fixture.detectChanges();

    const row = fixture.nativeElement.querySelector('.order-data-row') as HTMLElement;
    row.click();
    fixture.detectChanges();

    const detail = fixture.nativeElement.querySelector('.order-device-detail') as HTMLElement;
    expect(detail.textContent).toContain('<img src=x onerror=alert(1)>Не включается');
    expect(detail.querySelector('img')).toBeNull();
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});
