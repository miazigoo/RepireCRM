import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild
} from '@angular/core';
import { DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, map, takeUntil } from 'rxjs/operators';
import { OrdersService } from '../../../services/orders.service';
import { Order, OrderStatus, OrderPriority, OrderFilters } from '../../../core/models/models';

@Component({
  selector: 'app-orders-list',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    NgClass,
    DatePipe,
    RouterModule,
    ReactiveFormsModule,
    MatTableModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './orders-list.component.html',
  styleUrl: './orders-list.component.scss',
  providers: [
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: {
        appearance: 'outline',
        floatLabel: 'always'
      }
    }
  ]
})
export class OrdersListComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('loadMoreTrigger') loadMoreTrigger?: ElementRef<HTMLElement>;

  displayedColumns: string[] = [
    'order_number',
    'customer',
    'device',
    'status',
    'priority'
  ];

  detailColumns: string[] = ['order_details'];
  dataSource = new MatTableDataSource<Order>();
  filtersForm: FormGroup;
  loading = false;
  loadingMore = false;
  lastUpdatedAt: Date | null = null;
  expandedOrderId: number | null = null;
  totalOrdersCount = 0;

  private readonly pageSize = 20;
  private readonly destroy$ = new Subject<void>();
  private currentPage = 0;
  private totalPages = 0;
  private loadSubscription?: Subscription;
  private lazyObserver?: IntersectionObserver;

  readonly statusOptions: Array<{ value: OrderStatus | ''; label: string }> = [
    { value: '', label: 'Все статусы' },
    { value: 'received', label: 'Принят' },
    { value: 'diagnosed', label: 'Диагностирован' },
    { value: 'waiting_parts', label: 'Ожидание запчастей' },
    { value: 'in_repair', label: 'В ремонте' },
    { value: 'testing', label: 'Тестирование' },
    { value: 'ready', label: 'Готов' },
    { value: 'completed', label: 'Выдан' },
    { value: 'cancelled', label: 'Отменен' }
  ];

  readonly priorityOptions: Array<{ value: OrderPriority | ''; label: string }> = [
    { value: '', label: 'Все приоритеты' },
    { value: 'low', label: 'Низкий' },
    { value: 'normal', label: 'Обычный' },
    { value: 'high', label: 'Высокий' },
    { value: 'urgent', label: 'Срочный' }
  ];

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private ordersService: OrdersService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
    private router: Router
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      status: [''],
      priority: ['']
    });
  }

  ngOnInit(): void {
    this.loadOrders(true);
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.sortingDataAccessor = (order, property) => {
      switch (property) {
        case 'order_number':
          return order.order_number;
        case 'customer':
          return this.getCustomerFullName(order).toLowerCase();
        case 'device':
          return this.getDeviceTitle(order).toLowerCase();
        case 'cost':
          return this.getOrderAmount(order);
        case 'created_at':
          return new Date(order.created_at).getTime();
        default:
          return (order as any)[property];
      }
    };
    this.dataSource.sort = this.sort;
    this.setupLazyObserver();
  }

  ngOnDestroy(): void {
    this.lazyObserver?.disconnect();
    this.loadSubscription?.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
  }

  get orders(): Order[] {
    return this.dataSource.data;
  }

  get totalOrders(): number {
    return this.totalOrdersCount || this.orders.length;
  }

  get loadedOrders(): number {
    return this.orders.length;
  }

  get hasMoreOrders(): boolean {
    if (this.totalOrdersCount === 0) {
      return false;
    }
    return this.loadedOrders < this.totalOrdersCount && this.currentPage < this.totalPages;
  }

  get activeOrders(): number {
    return this.orders.filter(order => !['completed', 'cancelled'].includes(order.status)).length;
  }

  get readyOrders(): number {
    return this.orders.filter(order => order.status === 'ready').length;
  }

  get urgentOrders(): number {
    return this.orders.filter(order => order.priority === 'urgent' || order.priority === 'high').length;
  }

  get pipelineValue(): number {
    return this.orders
      .filter(order => order.status !== 'cancelled')
      .reduce((sum, order) => sum + this.getOrderAmount(order), 0);
  }

  get remainingTotal(): number {
    return this.orders.reduce((sum, order) => sum + Number(order.remaining_payment || 0), 0);
  }

  get hasActiveFilters(): boolean {
    const value = this.filtersForm.getRawValue();
    return Object.values(value).some(item => item !== '' && item !== null && item !== undefined);
  }

  loadNextPage(): void {
    this.loadOrders(false);
  }

  private loadOrders(reset: boolean): void {
    if (!reset && (this.loading || this.loadingMore || !this.hasMoreOrders)) {
      return;
    }

    if (reset) {
      this.loadSubscription?.unsubscribe();
      this.resetOrdersState();
      this.loading = true;
    } else {
      this.loadingMore = true;
    }

    const nextPage = reset ? 1 : this.currentPage + 1;
    const filters = this.getCleanFilters();

    this.loadSubscription = this.ordersService
      .getOrdersPage(nextPage, this.pageSize, filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          const existing = reset ? [] : this.dataSource.data;
          this.dataSource.data = this.mergeUniqueOrders(existing, response.items);
          this.currentPage = response.page;
          this.totalPages = response.total_pages;
          this.totalOrdersCount = response.count;
          this.lastUpdatedAt = new Date();
        },
        error: (error) => {
          console.error('Error loading orders:', error);
          this.snackBar.open('Ошибка загрузки заказов', 'Закрыть', { duration: 3000 });
          this.loading = false;
          this.loadingMore = false;
        },
        complete: () => {
          this.loading = false;
          this.loadingMore = false;
        }
      });
  }

  private resetOrdersState(): void {
    this.dataSource.data = [];
    this.currentPage = 0;
    this.totalPages = 0;
    this.totalOrdersCount = 0;
    this.expandedOrderId = null;
  }

  private getCleanFilters(): OrderFilters {
    const raw = this.filtersForm.getRawValue() as Record<string, string>;
    return Object.fromEntries(
      Object.entries(raw)
        .map(([key, value]) => [key, typeof value === 'string' ? value.trim() : value])
        .filter(([, value]) => value !== '' && value !== null && value !== undefined)
    ) as OrderFilters;
  }

  private mergeUniqueOrders(existing: Order[], incoming: Order[]): Order[] {
    const seen = new Set(existing.map(order => order.id));
    const next = incoming.filter(order => !seen.has(order.id));
    return [...existing, ...next];
  }

  private setupLazyObserver(): void {
    if (!this.loadMoreTrigger || !('IntersectionObserver' in window)) {
      return;
    }

    this.lazyObserver = new IntersectionObserver(
      entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          this.loadNextPage();
        }
      },
      { rootMargin: '360px 0px' }
    );
    this.lazyObserver.observe(this.loadMoreTrigger.nativeElement);
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges
      .pipe(
        debounceTime(300),
        map(value => JSON.stringify(value)),
        distinctUntilChanged(),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.loadOrders(true);
      });
  }

  clearFilters(): void {
    this.filtersForm.reset({
      search: '',
      status: '',
      priority: ''
    });
  }

  toggleOrderDetails(order: Order): void {
    this.expandedOrderId = this.expandedOrderId === order.id ? null : order.id;
  }

  isOrderExpanded(order: Order): boolean {
    return this.expandedOrderId === order.id;
  }

  openOrder(order: Order): void {
    this.router.navigate(['/orders', order.id]);
  }

  getStatusLabel(status: OrderStatus): string {
    const statusLabels: {[key in OrderStatus]: string} = {
      'received': 'Принят',
      'diagnosed': 'Диагностирован',
      'waiting_parts': 'Ожидание запчастей',
      'in_repair': 'В ремонте',
      'testing': 'Тестирование',
      'ready': 'Готов',
      'completed': 'Выдан',
      'cancelled': 'Отменен'
    };
    return statusLabels[status];
  }

  getPriorityLabel(priority: OrderPriority): string {
    const priorityLabels: {[key in OrderPriority]: string} = {
      'low': 'Низкий',
      'normal': 'Обычный',
      'high': 'Высокий',
      'urgent': 'Срочный'
    };
    return priorityLabels[priority];
  }

  getCustomerFullName(order: Order): string {
    return [order.customer.last_name, order.customer.first_name, order.customer.middle_name]
      .filter(Boolean)
      .join(' ');
  }

  getCustomerInitials(order: Order): string {
    const first = order.customer.first_name?.charAt(0) || '';
    const last = order.customer.last_name?.charAt(0) || '';
    return `${last}${first}`.toUpperCase() || 'К';
  }

  getDeviceTitle(order: Order): string {
    return [order.device.model.brand.name, order.device.model.name].filter(Boolean).join(' ');
  }

  getDeviceMeta(order: Order): string {
    return [order.device.color, order.device.storage_capacity].filter(Boolean).join(' · ') || 'Без уточнений';
  }

  getDeviceFacts(order: Order): Array<{ label: string; value: string }> {
    const facts = [
      { label: 'Тип', value: order.device.model.device_type?.name },
      { label: 'Цвет', value: order.device.color },
      { label: 'Память', value: order.device.storage_capacity },
      { label: 'Серийный номер', value: order.device.serial_number },
      { label: 'IMEI', value: order.device.imei },
      { label: 'Состояние', value: order.device_condition },
      { label: 'Комплектация', value: order.accessories }
    ];

    return facts
      .filter(item => Boolean(item.value))
      .map(item => ({ label: item.label, value: String(item.value) }));
  }

  getProblemSummary(order: Order): string {
    return order.problem_description || 'Описание неисправности пока не указано';
  }

  getWarrantySummary(order: Order): string {
    if (order.is_warranty_case) {
      return `Гарантия по ${order.warranty_parent_order_number || 'исходному заказу'}`;
    }
    if (order.warranty_active && order.warranty_until) {
      return `Гарантия до ${new Intl.DateTimeFormat('ru-RU').format(new Date(order.warranty_until))}`;
    }
    return '';
  }

  getOrderAmount(order: Order): number {
    return Number(order.final_cost ?? order.total_cost ?? order.cost_estimate ?? 0);
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, order: Order): number {
    return order.id;
  }
}
