import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
  InventoryProductGroup,
  InventoryService,
  PurchaseRequest,
  PurchaseRequestBatch,
  PurchaseRequestItem,
  PurchaseRequestTimelineEvent,
  Supplier
} from '../../../services/inventory.service';

@Component({
  selector: 'app-purchase-requests',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  templateUrl: './purchase-requests.component.html',
  styleUrl: './purchase-requests.component.scss'
})
export class PurchaseRequestsComponent implements OnInit {
  requests: PurchaseRequest[] = [];
  selectedRequest: PurchaseRequest | null = null;
  timeline: PurchaseRequestTimelineEvent[] = [];
  suppliers: Supplier[] = [];
  productGroups: InventoryProductGroup[] = [];
  loading = false;
  actionLoading = false;
  timelineLoading = false;
  filters = {
    status: '',
    supplierId: null as number | null,
    dueFrom: '',
    dueTo: '',
    search: ''
  };
  readonly statusOptions = [
    { value: '', label: 'Все статусы' },
    { value: 'submitted', label: 'На проверке' },
    { value: 'approved', label: 'Согласована' },
    { value: 'split', label: 'Разбита' },
    { value: 'sent', label: 'Отправлена' },
    { value: 'partially_received', label: 'Частично получена' },
    { value: 'received', label: 'Закрыта' },
    { value: 'rejected', label: 'Отклонена' }
  ];
  manualBatch = {
    supplierId: null as number | null,
    supplierName: '',
    groupName: '',
    title: '',
    notes: ''
  };
  manualQuantities: Record<number, number> = {};
  receiveQuantities: Record<number, number> = {};

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private inventoryService: InventoryService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadDictionaries();
    this.loadRequests();
  }

  private loadDictionaries(): void {
    this.inventoryService.getSuppliers().subscribe((suppliers) => {
      this.suppliers = suppliers;
    });
    this.inventoryService.getProductGroups().subscribe((groups) => {
      this.productGroups = groups;
    });
  }

  loadRequests(): void {
    this.loading = true;
    this.inventoryService.getPurchaseRequests({
      status: this.filters.status || null,
      supplier_id: this.filters.supplierId,
      due_from: this.filters.dueFrom || null,
      due_to: this.filters.dueTo || null,
      search: this.filters.search.trim() || null
    }).subscribe({
      next: (requests) => {
        this.requests = requests;
        const selectedId = this.selectedRequest?.id;
        this.selectedRequest = requests.find(item => item.id === selectedId) || requests[0] || null;
        this.resetManualBatch();
        this.resetReceiveQuantities();
        if (this.selectedRequest) {
          this.loadTimeline(this.selectedRequest.id);
        } else {
          this.timeline = [];
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Не удалось загрузить заявки', 'Закрыть', { duration: 3500 });
      }
    });
  }

  resetFilters(): void {
    this.filters = {
      status: '',
      supplierId: null,
      dueFrom: '',
      dueTo: '',
      search: ''
    };
    this.loadRequests();
  }

  selectRequest(request: PurchaseRequest): void {
    this.selectedRequest = request;
    this.inventoryService.getPurchaseRequest(request.id).subscribe({
      next: (detail) => {
        this.selectedRequest = detail;
        this.resetManualBatch();
        this.loadTimeline(detail.id);
      }
    });
  }

  createRequest(): void {
    this.router.navigate(['/inventory/purchase-requests/new']);
  }

  approve(): void {
    if (!this.selectedRequest || !this.canReviewSelected()) return;
    this.changeStatus('approved', 'Заявка согласована');
  }

  reject(): void {
    if (!this.selectedRequest || !this.canReviewSelected()) return;
    this.changeStatus('rejected', 'Заявка отклонена');
  }

  private changeStatus(status: string, successMessage: string): void {
    if (!this.selectedRequest) return;
    this.actionLoading = true;
    this.inventoryService.setPurchaseRequestStatus(this.selectedRequest.id, status).subscribe({
      next: (request) => {
        this.selectedRequest = request;
        this.actionLoading = false;
        this.snackBar.open(successMessage, 'Закрыть', { duration: 2500 });
        this.loadRequests();
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось изменить статус';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  split(mode: 'supplier' | 'group' | 'supplier_group'): void {
    if (!this.selectedRequest || !this.canSplitSelected()) return;
    this.actionLoading = true;
    this.inventoryService.splitPurchaseRequest(this.selectedRequest.id, mode).subscribe({
      next: () => {
        this.refreshSelected('Заявка разбита на документы');
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось разбить заявку';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  setManualQuantity(line: PurchaseRequestItem, value: number | string | null): void {
    const parsed = Math.floor(Number(value || 0));
    const safeValue = Number.isFinite(parsed) ? parsed : 0;
    this.manualQuantities[line.id] = Math.max(0, Math.min(safeValue, this.remainingQuantity(line)));
  }

  createManualBatch(): void {
    if (!this.selectedRequest || !this.canSplitSelected()) return;
    const items = this.selectedRequest.items
      .map((line) => ({
        request_item_id: line.id,
        quantity: Number(this.manualQuantities[line.id] || 0),
        unit_price: Number(line.unit_price || 0),
        notes: line.notes || ''
      }))
      .filter((line) => line.quantity > 0);

    if (!items.length) {
      this.snackBar.open('Укажите количество хотя бы по одной позиции', 'Закрыть', { duration: 3000 });
      return;
    }

    this.actionLoading = true;
    this.inventoryService.createPurchaseRequestBatch(this.selectedRequest.id, {
      supplier_id: this.manualBatch.supplierId || null,
      supplier_name: this.manualBatch.supplierId ? '' : this.manualBatch.supplierName.trim(),
      procurement_group_name: this.manualBatch.groupName.trim(),
      title: this.manualBatch.title.trim(),
      notes: this.manualBatch.notes.trim(),
      items
    }).subscribe({
      next: () => {
        this.resetManualBatch();
        this.refreshSelected('Документ поставщику создан');
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось создать документ';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  updateSupplier(line: PurchaseRequestItem, supplierId: number | null): void {
    if (!this.selectedRequest || !this.canEditSelectedItems()) return;
    this.inventoryService.updatePurchaseRequestItem(this.selectedRequest.id, line.id, {
      supplier_id: supplierId || null
    }).subscribe({
      next: () => this.refreshSelected('Поставщик обновлен', false),
      error: () => this.snackBar.open('Не удалось обновить поставщика', 'Закрыть', { duration: 3000 })
    });
  }

  updateGroup(line: PurchaseRequestItem, groupName: string): void {
    if (!this.selectedRequest || !this.canEditSelectedItems()) return;
    const normalized = String(groupName || '').trim();
    if ((line.procurement_group_name || '') === normalized) return;
    this.inventoryService.updatePurchaseRequestItem(this.selectedRequest.id, line.id, {
      procurement_group_name: normalized
    }).subscribe({
      next: () => this.refreshSelected('Группа обновлена', false),
      error: () => this.snackBar.open('Не удалось обновить группу', 'Закрыть', { duration: 3000 })
    });
  }

  downloadRequestPdf(): void {
    if (!this.selectedRequest) return;
    this.inventoryService.downloadPurchaseRequestPdf(this.selectedRequest.id).subscribe({
      next: (blob) => this.saveBlob(blob, `${this.selectedRequest?.request_number || 'purchase-request'}.pdf`),
      error: () => this.snackBar.open('Не удалось скачать PDF', 'Закрыть', { duration: 3000 })
    });
  }

  downloadBatchPdf(batch: PurchaseRequestBatch): void {
    if (!this.selectedRequest) return;
    this.inventoryService.downloadPurchaseRequestBatchPdf(this.selectedRequest.id, batch.id).subscribe({
      next: (blob) => this.saveBlob(blob, `${batch.batch_number}.pdf`),
      error: () => this.snackBar.open('Не удалось скачать PDF', 'Закрыть', { duration: 3000 })
    });
  }

  createOrderFromBatch(batch: PurchaseRequestBatch): void {
    if (!this.selectedRequest) return;
    if (!batch.supplier_id) {
      this.snackBar.open('Сначала укажите поставщика для документа', 'Закрыть', { duration: 3000 });
      return;
    }

    this.actionLoading = true;
    this.inventoryService.createPurchaseOrderFromBatch(this.selectedRequest.id, batch.id).subscribe({
      next: (result) => {
        const number = result?.order_number ? ` ${result.order_number}` : '';
        this.refreshSelected(`Заказ поставщику${number} создан`);
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось создать заказ поставщику';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  receiveBatchFull(batch: PurchaseRequestBatch): void {
    if (!this.selectedRequest) return;
    if (!batch.purchase_order_id) {
      this.snackBar.open('Сначала создайте заказ поставщику', 'Закрыть', { duration: 3000 });
      return;
    }

    this.actionLoading = true;
    this.inventoryService.receivePurchaseRequestBatchFull(this.selectedRequest.id, batch.id).subscribe({
      next: () => {
        this.refreshSelected('Поставка принята на склад');
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось принять поставку';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  setReceiveQuantity(line: { id: number; remaining_quantity?: number }, value: number | string | null): void {
    const parsed = Math.floor(Number(value || 0));
    const maxValue = Number(line.remaining_quantity || 0);
    const safeValue = Number.isFinite(parsed) ? parsed : 0;
    this.receiveQuantities[line.id] = Math.max(0, Math.min(safeValue, maxValue));
  }

  receiveBatchPartial(batch: PurchaseRequestBatch): void {
    if (!this.selectedRequest) return;
    if (!batch.purchase_order_id) {
      this.snackBar.open('Сначала создайте заказ поставщику', 'Закрыть', { duration: 3000 });
      return;
    }

    const items = batch.items
      .map((line) => ({
        batch_item_id: line.id,
        received_quantity: Number(this.receiveQuantities[line.id] || 0)
      }))
      .filter((line) => line.received_quantity > 0);
    if (!items.length) {
      this.snackBar.open('Укажите количество к приемке', 'Закрыть', { duration: 3000 });
      return;
    }

    this.actionLoading = true;
    this.inventoryService.receivePurchaseRequestBatch(this.selectedRequest.id, batch.id, items).subscribe({
      next: () => {
        this.resetReceiveQuantities();
        this.refreshSelected('Позиции приняты на склад');
      },
      error: (error) => {
        this.actionLoading = false;
        const message = error?.error?.error || 'Не удалось принять позиции';
        this.snackBar.open(message, 'Закрыть', { duration: 3500 });
      }
    });
  }

  private refreshSelected(message: string, showMessage = true): void {
    if (!this.selectedRequest) return;
    this.inventoryService.getPurchaseRequest(this.selectedRequest.id).subscribe({
      next: (request) => {
        this.selectedRequest = request;
        this.actionLoading = false;
        this.resetManualBatch();
        this.resetReceiveQuantities();
        this.loadTimeline(request.id);
        if (showMessage) {
          this.snackBar.open(message, 'Закрыть', { duration: 2500 });
        }
        this.loadRequests();
      },
      error: () => {
        this.actionLoading = false;
      }
    });
  }

  private loadTimeline(requestId: number): void {
    this.timelineLoading = true;
    this.inventoryService.getPurchaseRequestTimeline(requestId).subscribe({
      next: (events) => {
        this.timeline = events;
        this.timelineLoading = false;
      },
      error: () => {
        this.timeline = [];
        this.timelineLoading = false;
      }
    });
  }

  private saveBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  formatCurrency(value: number): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  batchedQuantity(line: PurchaseRequestItem): number {
    if (!this.selectedRequest?.batches?.length) return 0;
    return this.selectedRequest.batches.reduce((total, batch) => {
      const batchQuantity = batch.items
        .filter((item) => item.request_item_id === line.id)
        .reduce((sum, item) => sum + Number(item.quantity || 0), 0);
      return total + batchQuantity;
    }, 0);
  }

  remainingQuantity(line: PurchaseRequestItem): number {
    const approved = Number(line.approved_quantity || line.requested_quantity || 0);
    return Math.max(approved - this.batchedQuantity(line), 0);
  }

  manualSelectedTotal(): number {
    if (!this.selectedRequest) return 0;
    return this.selectedRequest.items.reduce((total, line) => {
      return total + Number(this.manualQuantities[line.id] || 0) * Number(line.unit_price || 0);
    }, 0);
  }

  batchReceiveTotal(batch: PurchaseRequestBatch): number {
    return batch.items.reduce((total, line) => {
      return total + Number(this.receiveQuantities[line.id] || 0) * Number(line.unit_price || 0);
    }, 0);
  }

  batchHasRemaining(batch: PurchaseRequestBatch): boolean {
    return batch.items.some((line) => Number(line.remaining_quantity || 0) > 0);
  }

  hasManualRemainder(): boolean {
    return !!this.selectedRequest?.items.some((line) => this.remainingQuantity(line) > 0);
  }

  canReviewSelected(): boolean {
    if (!this.selectedRequest) return false;
    return ['draft', 'submitted'].includes(this.selectedRequest.status);
  }

  canSplitSelected(): boolean {
    if (!this.selectedRequest) return false;
    return (
      ['draft', 'submitted', 'approved', 'split'].includes(this.selectedRequest.status) &&
      !this.hasPurchaseOrders(this.selectedRequest)
    );
  }

  canEditSelectedItems(): boolean {
    if (!this.selectedRequest) return false;
    return (
      ['draft', 'submitted', 'approved', 'split'].includes(this.selectedRequest.status) &&
      !this.hasPurchaseOrders(this.selectedRequest)
    );
  }

  private hasPurchaseOrders(request: PurchaseRequest): boolean {
    return request.batches.some((batch) => !!batch.purchase_order_id);
  }

  private resetManualBatch(): void {
    this.manualBatch = {
      supplierId: null,
      supplierName: '',
      groupName: '',
      title: '',
      notes: ''
    };
    this.manualQuantities = {};
  }

  private resetReceiveQuantities(): void {
    this.receiveQuantities = {};
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Черновик',
      submitted: 'На проверке',
      approved: 'Согласована',
      split: 'Разбита',
      sent: 'Отправлена',
      partially_received: 'Частично получена',
      received: 'Закрыта',
      rejected: 'Отклонена',
      cancelled: 'Отменена'
    };
    return labels[status] || status;
  }

  priorityLabel(priority: string): string {
    const labels: Record<string, string> = {
      low: 'Низкий',
      normal: 'Обычный',
      high: 'Высокий',
      urgent: 'Срочный'
    };
    return labels[priority] || priority;
  }

  eventIcon(event: PurchaseRequestTimelineEvent): string {
    if (event.event_type === 'request_status' || event.event_type === 'batch_status') {
      return 'swap_horiz';
    }
    const icons: Record<string, string> = {
      created: 'add_circle',
      updated: 'edit',
      status_changed: 'swap_horiz',
      split: 'account_tree',
      batch_created: 'post_add',
      order_created: 'inventory',
      received: 'inventory_2',
      pdf_downloaded: 'picture_as_pdf'
    };
    return icons[event.action || ''] || 'history';
  }

  timelineStatusText(event: PurchaseRequestTimelineEvent): string {
    if (!event.new_status) return '';
    const oldLabel = event.old_status ? this.statusLabel(event.old_status) : 'Старт';
    return `${oldLabel} -> ${this.statusLabel(event.new_status)}`;
  }

  trackById(_: number, item: { id: number }): number {
    return item.id;
  }

  trackByTimeline(_: number, item: PurchaseRequestTimelineEvent): string {
    return `${item.event_type}-${item.id}`;
  }
}
