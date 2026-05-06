// frontend/crm-app/src/app/features/orders/order-detail/order-detail.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, NgClass, DatePipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { finalize } from 'rxjs';
import { OrdersService } from '../../../services/orders.service';
import {
  Order,
  OrderApproval,
  OrderAuditLog,
  OrderStatusHistory,
  OrderStatus,
  RepairStage
} from '../../../core/models/models';

@Component({
  selector: 'app-order-detail',
  standalone: true,
  imports: [
    NgIf, NgFor, NgClass, DatePipe, RouterModule, ReactiveFormsModule,
    MatButtonModule, MatIconModule,
    MatDividerModule, MatMenuModule, MatSnackBarModule,
    MatProgressSpinnerModule, MatTabsModule, MatFormFieldModule,
    MatInputModule, MatCheckboxModule
  ],
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.scss',
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
export class OrderDetailComponent implements OnInit {
  order: Order | null = null;
  loading = false;
  stageSaving = false;
  approvalSaving = false;
  statusSaving = false;
  handoverSaving = false;
  handoverNeedsAttention = false;
  orderId: number;

  statusHistory: OrderStatusHistory[] = [];
  repairStages: RepairStage[] = [];
  approvals: OrderApproval[] = [];
  auditLogs: OrderAuditLog[] = [];
  orderDocuments: any[] = [];
  stageForm: FormGroup;
  approvalForm: FormGroup;
  handoverForm: FormGroup;
  selectedStagePhoto: File | null = null;

  readonly statusOptions: Array<{ value: OrderStatus; label: string; icon: string }> = [
    { value: 'received', label: 'Принят', icon: 'inbox' },
    { value: 'diagnosed', label: 'Диагностика', icon: 'search' },
    { value: 'waiting_parts', label: 'Ожидание запчастей', icon: 'inventory_2' },
    { value: 'in_repair', label: 'В ремонте', icon: 'build' },
    { value: 'testing', label: 'Тестирование', icon: 'fact_check' },
    { value: 'ready', label: 'Готов', icon: 'task_alt' },
    { value: 'completed', label: 'Выдан', icon: 'done_all' },
    { value: 'cancelled', label: 'Отменен', icon: 'cancel' }
  ];

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private ordersService: OrdersService,
    private snackBar: MatSnackBar,
    private fb: FormBuilder
  ) {
    this.orderId = +this.route.snapshot.params['id'];
    this.stageForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(120)]],
      description: [''],
      customer_visible: [true]
    });
    this.approvalForm = this.fb.group({
      title: ['Согласование стоимости ремонта', [Validators.required, Validators.maxLength(160)]],
      description: [''],
      amount: [0, [Validators.required, Validators.min(0)]]
    });
    this.handoverForm = this.fb.group({
      final_cost: [0, [Validators.required, Validators.min(0)]],
      prepayment: [0, [Validators.required, Validators.min(0)]],
      status_comment: ['Заказ выдан клиенту', [Validators.maxLength(255)]]
    });
  }

  ngOnInit(): void {
    this.loadOrder();
    this.loadStatusHistory();
    this.loadRepairStages();
    this.loadApprovals();
    this.loadAuditLog();
    this.loadDocuments();
  }

  private loadOrder(): void {
    this.loading = true;
    this.ordersService.getOrder(this.orderId).subscribe({
      next: (order) => {
        this.order = order;
        this.syncHandoverForm(order);
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

  private loadApprovals(): void {
    this.ordersService.getApprovals(this.orderId).subscribe({
      next: (items) => this.approvals = items,
      error: () => this.snackBar.open('Ошибка загрузки согласований', 'Закрыть', { duration: 3000 })
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
    this.snackBar.open('Выберите новый статус в шкале заказа', 'Закрыть', { duration: 2500 });
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

  requestApproval(): void {
    if (this.approvalForm.invalid || this.approvalSaving) {
      return;
    }

    this.approvalSaving = true;
    this.ordersService.requestApproval(this.orderId, this.approvalForm.getRawValue())
      .pipe(finalize(() => this.approvalSaving = false))
      .subscribe({
        next: () => {
          this.snackBar.open('Согласование отправлено клиенту', 'Закрыть', { duration: 2500 });
          this.approvalForm.reset({
            title: 'Согласование стоимости ремонта',
            description: '',
            amount: 0
          });
          this.loadApprovals();
          this.loadAuditLog();
        },
        error: (error) => {
          const message = error.error?.error || 'Не удалось отправить согласование';
          this.snackBar.open(message, 'Закрыть', { duration: 3500 });
        }
      });
  }

  setOrderStatus(status: OrderStatus): void {
    if (!this.order || this.order.status === status || this.statusSaving) {
      return;
    }

    if (status === 'completed') {
      this.syncHandoverForm(this.order);
      this.handoverNeedsAttention = true;
      this.snackBar.open('Укажите итоговую стоимость в блоке выдачи заказа', 'Закрыть', {
        duration: 3500
      });
      return;
    }

    const previousStatus = this.order.status;
    this.statusSaving = true;
    this.ordersService.updateOrder(this.orderId, {
      status,
      status_comment: 'Изменено из карточки заказа'
    }).pipe(finalize(() => this.statusSaving = false))
      .subscribe({
        next: (order) => {
          this.order = order;
          this.snackBar.open('Статус заказа обновлен', 'Закрыть', { duration: 2500 });
          this.loadStatusHistory();
          this.loadAuditLog();
        },
        error: (error) => {
          const message = error.error?.error || 'Не удалось изменить статус заказа';
          this.snackBar.open(message, 'Закрыть', { duration: 3500 });
          if (this.order) {
            this.order = { ...this.order, status: previousStatus };
          }
        }
      });
  }

  completeOrder(): void {
    if (!this.order || this.handoverSaving) {
      return;
    }

    if (this.handoverForm.invalid) {
      this.handoverForm.markAllAsTouched();
      this.handoverNeedsAttention = true;
      this.snackBar.open('Проверьте итоговую стоимость и предоплату', 'Закрыть', {
        duration: 3000
      });
      return;
    }

    const value = this.handoverForm.getRawValue();
    const finalCost = Number(value.final_cost || 0);
    const prepayment = Number(value.prepayment || 0);
    const statusComment = String(value.status_comment || '').trim() || 'Заказ выдан клиенту';

    this.handoverSaving = true;
    this.ordersService.updateOrder(this.orderId, {
      status: 'completed',
      final_cost: finalCost,
      prepayment,
      status_comment: statusComment
    }).pipe(finalize(() => this.handoverSaving = false))
      .subscribe({
        next: (order) => {
          this.order = order;
          this.syncHandoverForm(order);
          this.handoverNeedsAttention = false;
          this.snackBar.open('Заказ выдан клиенту', 'Закрыть', { duration: 2500 });
          this.loadStatusHistory();
          this.loadAuditLog();
        },
        error: (error) => {
          const message = error.error?.error || 'Не удалось выдать заказ';
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
    return [
      order.device.color,
      order.device.storage_capacity,
      order.device.serial_number ? `SN ${order.device.serial_number}` : '',
      order.device.imei ? `IMEI ${order.device.imei}` : ''
    ].filter(Boolean).join(' · ') || 'Без уточнений';
  }

  getOrderAmount(order: Order): number {
    return Number(order.final_cost ?? order.total_cost ?? order.cost_estimate ?? 0);
  }

  get handoverServicesTotal(): number {
    return this.order?.additional_services?.reduce(
      (sum, service) => sum + Number(service.total_price || 0),
      0
    ) || 0;
  }

  get handoverTotal(): number {
    const finalCost = Number(this.handoverForm.get('final_cost')?.value || 0);
    return finalCost + this.handoverServicesTotal;
  }

  get handoverRemaining(): number {
    const prepayment = Number(this.handoverForm.get('prepayment')?.value || 0);
    return Math.max(0, this.handoverTotal - prepayment);
  }

  getWorkSummary(order: Order): string {
    return order.diagnosis || order.work_description || order.problem_description || 'Описание пока не заполнено';
  }

  getCompletionLabel(order: Order): string {
    if (order.completed_at) {
      return 'Завершен';
    }
    if (order.estimated_completion) {
      return 'План';
    }
    return 'Срок';
  }

  getCompletionValue(order: Order): string {
    if (order.completed_at) {
      return order.completed_at;
    }
    return order.estimated_completion || order.created_at;
  }

  getStatusIndex(status: OrderStatus): number {
    return this.statusOptions.findIndex(option => option.value === status);
  }

  isStatusDone(status: OrderStatus): boolean {
    if (!this.order || this.order.status === 'cancelled') {
      return false;
    }

    return this.getStatusIndex(status) < this.getStatusIndex(this.order.status);
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, item: { id: number }): number {
    return item.id;
  }

  openDocument(url: string): void {
    window.open(url, '_blank');
  }

  private syncHandoverForm(order: Order): void {
    const finalCost = Number(order.final_cost ?? order.cost_estimate ?? 0);
    const prepayment = Number(order.prepayment || 0);

    this.handoverForm.patchValue({
      final_cost: finalCost,
      prepayment,
      status_comment: 'Заказ выдан клиенту'
    }, { emitEvent: false });
  }
}
