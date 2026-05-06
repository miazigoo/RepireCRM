import { Component, OnInit, ViewChild } from '@angular/core';
import { DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { OrdersService } from '../../../services/orders.service';
import { Order, OrderStatus, OrderPriority } from '../../../core/models/models';

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
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    MatSnackBarModule,
    MatDividerModule
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
export class OrdersListComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'order_number',
    'customer',
    'device',
    'status',
    'priority',
    'cost',
    'created_at',
    'actions'
  ];

  dataSource = new MatTableDataSource<Order>();
  filtersForm: FormGroup;
  loading = false;
  lastUpdatedAt: Date | null = null;

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
    this.loadOrders();
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
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  get orders(): Order[] {
    return this.dataSource.data;
  }

  get totalOrders(): number {
    return this.orders.length;
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

  private loadOrders(): void {
    this.loading = true;
    const filters = this.filtersForm.value;

    this.ordersService.getOrders(1, 100, filters).subscribe({
      next: (orders) => {
        this.dataSource.data = orders;
        this.lastUpdatedAt = new Date();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading orders:', error);
        this.snackBar.open('Ошибка загрузки заказов', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged()
      )
      .subscribe(() => {
        this.loadOrders();
      });
  }

  clearFilters(): void {
    this.filtersForm.reset({
      search: '',
      status: '',
      priority: ''
    });
  }

  changeStatus(order: Order): void {
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
