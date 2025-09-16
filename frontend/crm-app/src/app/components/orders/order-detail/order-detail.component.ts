// frontend/crm-app/src/app/features/orders/order-detail/order-detail.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, NgClass, DatePipe, CurrencyPipe } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { OrdersService } from '../../../services/orders.service';
import { Order } from '../../../core/models/models';

@Component({
  selector: 'app-order-detail',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, CurrencyPipe, RouterModule,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatDividerModule, MatMenuModule, MatDialogModule, MatSnackBarModule,
    MatProgressSpinnerModule, MatTabsModule, MatTableModule
  ],
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.css'
})
export class OrderDetailComponent implements OnInit {
  order: Order | null = null;
  loading = false;
  orderId: number;

  statusHistory: any[] = [];
  orderDocuments: any[] = [];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private ordersService: OrdersService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.orderId = +this.route.snapshot.params['id'];
  }

  ngOnInit(): void {
    this.loadOrder();
    this.loadStatusHistory();
    this.loadDocuments();
  }

  private loadOrder(): void {
    this.loading = true;
    this.ordersService.getOrder(this.orderId).subscribe({
      next: (order) => {
        this.order = order;
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Ошибка загрузки заказа', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private loadStatusHistory(): void {
    // Load status change history
    this.statusHistory = [
      {
        status: 'received',
        date: new Date('2024-01-15T10:00:00'),
        user: 'Иванов И.И.',
        comment: 'Заказ принят'
      },
      {
        status: 'diagnosed',
        date: new Date('2024-01-15T14:30:00'),
        user: 'Петров П.П.',
        comment: 'Требуется замена экрана'
      }
    ];
  }

  private loadDocuments(): void {
    // Load order documents
    this.orderDocuments = [
      {
        id: 1,
        type: 'receipt',
        name: 'Квитанция о приеме',
        created_at: new Date('2024-01-15T10:00:00'),
        file_url: '/documents/receipt_001.pdf'
      }
    ];
  }

  editOrder(): void {
    this.router.navigate(['/orders', this.orderId, 'edit']);
  }

  changeStatus(): void {
    // Open status change dialog
    console.log('Change status');
  }

  printReceipt(): void {
    // Print receipt logic
    console.log('Print receipt');
  }

  sendNotification(): void {
    // Send notification to customer
    console.log('Send notification');
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

  getPriorityLabel(priority: string): string {
    const priorityLabels: {[key: string]: string} = {
      'low': 'Низкий',
      'normal': 'Обычный',
      'high': 'Высокий',
      'urgent': 'Срочный'
    };
    return priorityLabels[priority] || priority;
  }

  getStatusIcon(status: string): string {
    const statusIcons: {[key: string]: string} = {
      'received': 'inbox',
      'diagnosed': 'search',
      'waiting_parts': 'hourglass_empty',
      'in_repair': 'build',
      'testing': 'bug_report',
      'ready': 'check_circle',
      'completed': 'done_all',
      'cancelled': 'cancel'
    };
    return statusIcons[status] || 'help';
  }

  openDocument(url: string): void {
    window.open(url, '_blank');
  }
}
