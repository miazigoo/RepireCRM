import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, RouterLink } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Order } from '../../core/models/models';
import { OrdersService } from '../../services/orders.service';
import { ThemeService } from '../../services/theme.service';
import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let ordersService: jasmine.SpyObj<OrdersService>;

  const stats = {
    total_orders: 3,
    total_revenue: 72000,
    avg_order_value: 24000,
    recent_orders: 2,
    recent_revenue: 42000,
    status_distribution: [
      { status: 'received', count: 2 },
      { status: 'ready', count: 1 },
    ],
    period: '30 days',
  };

  const recentOrder = {
    id: 7,
    order_number: 'ORD-007',
    status: 'ready',
    cost_estimate: 18000,
    final_cost: 24000,
    total_cost: 24000,
    created_at: '2026-05-05T10:30:00Z',
    customer: {
      first_name: 'Иван',
      last_name: 'Петров',
    },
    device: {
      model: {
        name: 'iPhone 15 Pro',
        brand: { name: 'Apple' },
      },
    },
  } as Order;

  beforeEach(async () => {
    ordersService = jasmine.createSpyObj<OrdersService>('OrdersService', [
      'getStatistics',
      'getOrders',
    ]);

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: OrdersService, useValue: ordersService },
        {
          provide: ThemeService,
          useValue: {
            currentTheme$: of({}),
            currentStyle$: of({}),
            currentSkin$: of({}),
          },
        },
      ],
    }).compileComponents();
  });

  it('renders the redesigned dashboard summary and command links', () => {
    ordersService.getStatistics.and.returnValue(of(stats));
    ordersService.getOrders.and.returnValue(of([recentOrder]));

    fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();

    const text = normalizeText(fixture.nativeElement);
    expect(text).toContain('Операционный центр');
    expect(text).toContain('Операционная воронка');
    expect(text).toContain('42 000 ₽');
    expect(text).toContain('Apple iPhone 15 Pro');
    expect(text).toContain('Заказ поставщику');
    expect(fixture.nativeElement.querySelectorAll('.metric-icon svg').length).toBe(4);

    const targets = fixture.debugElement
      .queryAll(By.directive(RouterLink))
      .map((debugElement) => debugElement.injector.get(RouterLink).urlTree!.toString());

    expect(targets).toContain('/orders/new');
    expect(targets).toContain('/inventory/purchase-orders/new');
    expect(targets).toContain('/orders');
  });

  it('shows polished empty states when the shop has no orders', () => {
    ordersService.getStatistics.and.returnValue(
      of({
        ...stats,
        total_orders: 0,
        total_revenue: 0,
        avg_order_value: 0,
        recent_orders: 0,
        recent_revenue: 0,
        status_distribution: [],
      })
    );
    ordersService.getOrders.and.returnValue(of([]));

    fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();

    const text = normalizeText(fixture.nativeElement);
    expect(text).toContain('Статусов пока нет');
    expect(text).toContain('Заказов пока нет');
    expect(text).toContain('Создать заказ');
    expect(fixture.nativeElement.querySelectorAll('.empty-icon svg').length).toBe(2);
  });

  it('surfaces load errors without breaking the dashboard shell', () => {
    ordersService.getStatistics.and.returnValue(throwError(() => new Error('stats')));
    ordersService.getOrders.and.returnValue(throwError(() => new Error('orders')));

    fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();

    const text = normalizeText(fixture.nativeElement);
    expect(text).toContain('Панель управления');
    expect(text).toContain('Статистика временно недоступна');
    expect(text).toContain('Не удалось загрузить последние заказы');
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});
