// frontend/crm-app/src/app/features/orders/order-detail/order-detail.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, NgClass, DatePipe, CurrencyPipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
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
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { finalize } from 'rxjs';
import { OrdersService } from '../../../services/orders.service';
import { Order, OrderAuditLog, OrderStatusHistory, RepairStage } from '../../../core/models/models';

@Component({
  selector: 'app-order-detail',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, CurrencyPipe, RouterModule, ReactiveFormsModule,
    MatCardModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatDividerModule, MatMenuModule, MatDialogModule, MatSnackBarModule,
    MatProgressSpinnerModule, MatTabsModule, MatTableModule, MatFormFieldModule,
    MatInputModule, MatCheckboxModule
  ],
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.css'
})
export class OrderDetailComponent implements OnInit {
  order: Order | null = null;
  loading = false;
  stageSaving = false;
  orderId: number;

  statusHistory: OrderStatusHistory[] = [];
  repairStages: RepairStage[] = [];
  auditLogs: OrderAuditLog[] = [];
  orderDocuments: any[] = [];
  stageForm: FormGroup;
  selectedStagePhoto: File | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private ordersService: OrdersService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private fb: FormBuilder
  ) {
    this.orderId = +this.route.snapshot.params['id'];
    this.stageForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(120)]],
      description: [''],
      customer_visible: [true]
    });
  }

  ngOnInit(): void {
    this.loadOrder();
    this.loadStatusHistory();
    this.loadRepairStages();
    this.loadAuditLog();
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
    this.ordersService.getStatusHistory(this.orderId).subscribe({
      next: (items) => this.statusHistory = items,
      error: () => this.snackBar.open('Ошибка загрузки истории статусов', 'Закрыть', { duration: 3000 })
    });
  }

  private loadRepairStages(): void {
    this.ordersService.getRepairStages(this.orderId).subscribe({
      next: (items) => this.repairStages = items,
      error: () => this.snackBar.open('Ошибка загрузки этапов ремонта', 'Закрыть', { duration: 3000 })
    });
  }

  private loadAuditLog(): void {
    this.ordersService.getAuditLog(this.orderId).subscribe({
      next: (items) => this.auditLogs = items,
      error: () => this.snackBar.open('Ошибка загрузки журнала действий', 'Закрыть', { duration: 3000 })
    });
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

  onStagePhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedStagePhoto = input.files?.[0] || null;
  }

  addRepairStage(): void {
    if (this.stageForm.invalid || this.stageSaving) {
      return;
    }

    const formValue = this.stageForm.getRawValue();
    const data = new FormData();
    data.append('title', formValue.title);
    data.append('description', formValue.description || '');
    data.append('customer_visible', String(formValue.customer_visible));
    if (this.selectedStagePhoto) {
      data.append('photo', this.selectedStagePhoto);
    }

    this.stageSaving = true;
    this.ordersService.addRepairStage(this.orderId, data)
      .pipe(finalize(() => this.stageSaving = false))
      .subscribe({
        next: () => {
          this.snackBar.open('Этап ремонта добавлен', 'Закрыть', { duration: 2500 });
          this.stageForm.reset({ title: '', description: '', customer_visible: true });
          this.selectedStagePhoto = null;
          this.loadRepairStages();
          this.loadAuditLog();
        },
        error: (error) => {
          const message = error.error?.error || 'Не удалось добавить этап ремонта';
          this.snackBar.open(message, 'Закрыть', { duration: 3500 });
        }
      });
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
