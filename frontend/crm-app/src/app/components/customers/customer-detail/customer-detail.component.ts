import { Component, OnInit } from '@angular/core';
import { NgClass, NgFor, NgIf, DatePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { CustomersService } from '../../../services/customers.service';
import { Customer } from '../../../core/models/models';

@Component({
  selector: 'app-customer-detail',
  standalone: true,
  imports: [
    NgIf, NgFor, NgClass, DatePipe, RouterModule,
    MatButtonModule, MatIconModule, MatDividerModule, MatMenuModule,
    MatProgressSpinnerModule, MatSnackBarModule
  ],
  templateUrl: './customer-detail.component.html',
  styleUrl: './customer-detail.component.scss'
})
export class CustomerDetailComponent implements OnInit {
  customer: Customer | null = null;
  customerOrders: any[] = [];
  loading = false;
  customerId: number;
  lastUpdatedAt: Date | null = null;

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

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
        this.lastUpdatedAt = new Date();
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

  openWarranty(order: any): void {
    this.router.navigate(['/orders', order.id], {
      queryParams: { warranty: 'new' }
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

  getChannelLabel(channel?: string): string {
    const channelLabels: {[key: string]: string} = {
      'email': 'Email',
      'sms': 'SMS'
    };
    return channel ? channelLabels[channel] || channel : 'Не выбран';
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

  getOrderAmount(order: any): number {
    return Number(order.final_cost || order.cost_estimate || 0);
  }

  canCreateWarranty(order: any): boolean {
    return Boolean(!order.is_warranty_case && order.status === 'completed' && order.warranty_active);
  }

  getWarrantyLabel(order: any): string {
    if (order.is_warranty_case) {
      return `Гарантийный по ${order.warranty_parent_order_number || 'исходному заказу'}`;
    }
    if (order.warranty_active && order.warranty_until) {
      return `Гарантия до ${new Intl.DateTimeFormat('ru-RU').format(new Date(order.warranty_until))}`;
    }
    return '';
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, item: { id: number }): number {
    return item.id;
  }
}
