// frontend/crm-app/src/app/features/customers/customer-detail/customer-detail.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, DatePipe, CurrencyPipe } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { CustomersService } from '../../../services/customers.service';
import { Customer } from '../../../core/models/models';

@Component({
  selector: 'app-customer-detail',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, CurrencyPipe, RouterModule,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatDividerModule, MatMenuModule, MatProgressSpinnerModule,
    MatSnackBarModule, MatTableModule, MatTabsModule
  ],
  templateUrl: './customer-detail.component.html',
  styleUrl: './customer-detail.component.css'
})
export class CustomerDetailComponent implements OnInit {
  customer: Customer | null = null;
  customerOrders: any[] = [];
  loading = false;
  customerId: number;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private customersService: CustomersService,
    private snackBar: MatSnackBar
  ) {
    this.customerId = +this.route.snapshot.params['id'];
  }

  ngOnInit(): void {
    this.loadCustomer();
    this.loadCustomerOrders();
  }

  private loadCustomer(): void {
    this.loading = true;
    this.customersService.getCustomer(this.customerId).subscribe({
      next: (customer) => {
        this.customer = customer;
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Ошибка загрузки клиента', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private loadCustomerOrders(): void {
    this.customersService.getCustomerOrders(this.customerId).subscribe({
      next: (orders) => {
        this.customerOrders = orders;
      },
      error: (error) => {
        console.error('Error loading customer orders:', error);
      }
    });
  }

  editCustomer(): void {
    this.router.navigate(['/customers', this.customerId, 'edit']);
  }

  createOrder(): void {
    this.router.navigate(['/orders/new'], {
      queryParams: { customer_id: this.customerId }
    });
  }

  deleteCustomer(): void {
    if (this.customer && this.customer.orders_count > 0) {
      this.snackBar.open('Нельзя удалить клиента с заказами', 'Закрыть', { duration: 3000 });
      return;
    }

    if (confirm(`Удалить клиента ${this.customer?.last_name} ${this.customer?.first_name}?`)) {
      this.customersService.deleteCustomer(this.customerId).subscribe({
        next: () => {
          this.snackBar.open('Клиент удален', 'Закрыть', { duration: 3000 });
          this.router.navigate(['/customers']);
        },
        error: (error) => {
          this.snackBar.open('Ошибка удаления клиента', 'Закрыть', { duration: 3000 });
        }
      });
    }
  }

  getSourceLabel(source: string): string {
    const sourceLabels: {[key: string]: string} = {
      'website': 'Сайт',
      'social': 'Социальные сети',
      'referral': 'Рекомендация',
      'advertising': 'Реклама',
      'walk_in': 'Зашел с улицы',
      'other': 'Другое'
    };
    return sourceLabels[source] || source;
  }

  getStatusLabel(status: string): string {
    const statusLabels: {[key: string]: string} = {
      'received': 'Принят',
      'diagnosed': 'Диагностирован',
      'waiting_parts': 'Ожидание запчастей',
      'in_repair': 'В ремонте',
      'testing': 'Тестирование',
      'ready': 'Готов',
      'completed': 'Выдан',
      'cancelled': 'Отменен'
    };
    return statusLabels[status] || status;
  }
}
