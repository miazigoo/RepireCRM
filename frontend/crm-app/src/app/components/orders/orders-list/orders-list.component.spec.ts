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
      model: {
        id: 1,
        name: 'iPhone 13',
        brand: { id: 1, name: 'Apple' },
        device_type: { id: 1, name: 'Смартфон' },
      },
    },
  } as Order;

  beforeEach(async () => {
    ordersService = jasmine.createSpyObj<OrdersService>('OrdersService', ['getOrders']);
    ordersService.getOrders.and.returnValue(of([order]));

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

    expect(text).toContain('Сервисная очередь');
    expect(text).toContain('Рабочий список');
    expect(text).toContain('ORD-SPB01-000002');
    expect(text).toContain('900 ₽');
    expect(text).not.toContain('RUB');
    expect(fixture.nativeElement.querySelector('.orders-page')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('mat-card')).toBeFalsy();
  });

  it('exposes operational metrics from the loaded orders', () => {
    expect(component.totalOrders).toBe(1);
    expect(component.activeOrders).toBe(1);
    expect(component.urgentOrders).toBe(1);
    expect(component.pipelineValue).toBe(900);
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});
