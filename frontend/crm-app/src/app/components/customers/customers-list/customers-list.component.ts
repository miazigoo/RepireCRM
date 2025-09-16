// frontend/crm-app/src/app/features/customers/customers-list/customers-list.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor, DatePipe, CurrencyPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { CustomersService } from '../../../services/customers.service';
import { Customer } from '../../../core/models/models';
import { MatDividerModule } from '@angular/material/divider'; 

@Component({
  selector: 'app-customers-list',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, CurrencyPipe, RouterModule, ReactiveFormsModule,
    MatTableModule, MatPaginatorModule, MatSortModule, MatInputModule,
    MatSelectModule, MatButtonModule, MatIconModule, MatCardModule,
    MatProgressSpinnerModule, MatMenuModule, MatChipsModule,
    MatDialogModule, MatSnackBarModule, MatDividerModule
  ],
  templateUrl: './customers-list.component.html',
  styleUrl: './customers-list.component.css'
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
    private dialog: MatDialog,
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

  private loadCustomers(): void {
    this.loading = true;
    const filters = this.filtersForm.value;

    this.customersService.getCustomers(1, 100, filters).subscribe({
      next: (customers) => {
        this.dataSource.data = customers;
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
    this.filtersForm.reset();
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
}
