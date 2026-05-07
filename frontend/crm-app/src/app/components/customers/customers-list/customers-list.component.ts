// frontend/crm-app/src/app/features/customers/customers-list/customers-list.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { CustomersService } from '../../../services/customers.service';
import { Customer } from '../../../core/models/models';
import { MatDividerModule } from '@angular/material/divider';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';

@Component({
  selector: 'app-customers-list',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, RouterModule, ReactiveFormsModule,
    MatTableModule, MatPaginatorModule, MatSortModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatMenuModule,
    MatSnackBarModule, MatDividerModule
  ],
  templateUrl: './customers-list.component.html',
  styleUrl: './customers-list.component.scss',
  providers: [
    { provide: MatPaginatorIntl, useClass: RussianPaginatorIntl },
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: {
        appearance: 'outline',
        floatLabel: 'always'
      }
    }
  ]
})
export class CustomersListComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'name',
    'phone',
    'email',
    'orders_count',
    'total_spent',
    'source',
    'created_at',
    'actions'
  ];

  dataSource = new MatTableDataSource<Customer>();
  filtersForm: FormGroup;
  loading = false;
  lastUpdatedAt: Date | null = null;

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  sourceOptions = [
    { value: 'website', label: 'Сайт' },
    { value: 'social', label: 'Социальные сети' },
    { value: 'referral', label: 'Рекомендация' },
    { value: 'advertising', label: 'Реклама' },
    { value: 'walk_in', label: 'Зашел с улицы' },
    { value: 'other', label: 'Другое' }
  ];

  constructor(
    private customersService: CustomersService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      source: [''],
      has_orders: [''],
      created_from: [''],
      created_to: ['']
    });
  }

  ngOnInit(): void {
    this.loadCustomers();
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  get customers(): Customer[] {
    return this.dataSource.data;
  }

  get totalCustomers(): number {
    return this.customers.length;
  }

  get customersWithOrders(): number {
    return this.customers.filter(customer => Number(customer.orders_count || 0) > 0).length;
  }

  get ordersTotal(): number {
    return this.customers.reduce((sum, customer) => sum + Number(customer.orders_count || 0), 0);
  }

  get revenueTotal(): number {
    return this.customers.reduce((sum, customer) => sum + Number(customer.total_spent || 0), 0);
  }

  get averageSpent(): number {
    return this.customersWithOrders > 0 ? this.revenueTotal / this.customersWithOrders : 0;
  }

  get newCustomersThisMonth(): number {
    const now = new Date();
    return this.customers.filter(customer => {
      const createdAt = new Date(customer.created_at);
      return createdAt.getMonth() === now.getMonth() && createdAt.getFullYear() === now.getFullYear();
    }).length;
  }

  get topSourceLabel(): string {
    const sources = this.sourceOptions
      .map(option => ({
        label: option.label,
        count: this.customers.filter(customer => customer.source === option.value).length
      }))
      .filter(item => item.count > 0)
      .sort((a, b) => b.count - a.count);

    return sources[0]?.label || 'Нет данных';
  }

  get hasActiveFilters(): boolean {
    const value = this.filtersForm.getRawValue();
    return Object.values(value).some(item => item !== '' && item !== null && item !== undefined);
  }

  private loadCustomers(): void {
    this.loading = true;
    const filters = this.filtersForm.value;

    this.customersService.getCustomers(1, 100, filters).subscribe({
      next: (customers) => {
        this.dataSource.data = customers;
        this.lastUpdatedAt = new Date();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading customers:', error);
        this.snackBar.open('Ошибка загрузки клиентов', 'Закрыть', { duration: 3000 });
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
        this.loadCustomers();
      });
  }

  clearFilters(): void {
    this.filtersForm.reset({
      search: '',
      source: '',
      has_orders: '',
      created_from: '',
      created_to: ''
    });
  }

  deleteCustomer(customer: Customer): void {
    if (customer.orders_count > 0) {
      this.snackBar.open('Нельзя удалить клиента с заказами', 'Закрыть', { duration: 3000 });
      return;
    }

    if (confirm(`Удалить клиента ${customer.last_name} ${customer.first_name}?`)) {
      this.customersService.deleteCustomer(customer.id).subscribe({
        next: () => {
          this.snackBar.open('Клиент удален', 'Закрыть', { duration: 3000 });
          this.loadCustomers();
        },
        error: (error) => {
          this.snackBar.open('Ошибка удаления клиента', 'Закрыть', { duration: 3000 });
        }
      });
    }
  }

  getSourceLabel(source: string): string {
    const option = this.sourceOptions.find(opt => opt.value === source);
    return option ? option.label : source;
  }

  getCustomerFullName(customer: Customer): string {
    return [customer.last_name, customer.first_name, customer.middle_name].filter(Boolean).join(' ');
  }

  getCustomerInitials(customer: Customer): string {
    const first = customer.first_name?.charAt(0) || '';
    const last = customer.last_name?.charAt(0) || '';
    return `${last}${first}`.toUpperCase() || 'К';
  }

  getCustomerTier(customer: Customer): string {
    const spent = Number(customer.total_spent || 0);
    const orders = Number(customer.orders_count || 0);

    if (spent >= 50000 || orders >= 10) {
      return 'VIP';
    }

    if (spent >= 15000 || orders >= 3) {
      return 'Лояльный';
    }

    return orders > 0 ? 'Активный' : 'Новый';
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, customer: Customer): number {
    return customer.id;
  }
}
