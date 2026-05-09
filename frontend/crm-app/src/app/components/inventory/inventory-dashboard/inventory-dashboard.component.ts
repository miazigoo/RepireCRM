import { AfterViewInit, Component, Inject, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import {
  InventoryItem,
  InventoryService,
  StockAlert,
  Supplier,
  UpdateInventoryItemRequest,
} from '../../../services/inventory.service';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';

interface InventoryItemEditDialogData {
  item: InventoryItem;
  suppliers: Supplier[];
  itemTypes: Array<{ value: string; label: string }>;
}

@Component({
  selector: 'app-inventory-item-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule
  ],
  template: `
    <header class="edit-dialog-header">
      <div>
        <span>Карточка товара</span>
        <h2 mat-dialog-title>Редактирование позиции</h2>
      </div>
      <button mat-icon-button type="button" aria-label="Закрыть" (click)="close()">
        <mat-icon>close</mat-icon>
      </button>
    </header>

    <mat-dialog-content>
      <form [formGroup]="form" class="edit-form">
        <mat-form-field class="span-2">
          <mat-label>Название</mat-label>
          <input matInput formControlName="name" autocomplete="off">
          <mat-error *ngIf="form.get('name')?.hasError('required')">
            Укажите название
          </mat-error>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Артикул</mat-label>
          <input matInput formControlName="sku" autocomplete="off">
          <mat-error *ngIf="form.get('sku')?.hasError('required')">
            Укажите артикул
          </mat-error>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Тип</mat-label>
          <mat-select formControlName="item_type">
            <mat-option *ngFor="let type of data.itemTypes" [value]="type.value">
              {{ type.label }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Категория</mat-label>
          <input matInput formControlName="category_name" autocomplete="off">
        </mat-form-field>

        <mat-form-field>
          <mat-label>Поставщик</mat-label>
          <mat-select formControlName="primary_supplier_id">
            <mat-option [value]="null">Не указан</mat-option>
            <mat-option *ngFor="let supplier of data.suppliers" [value]="supplier.id">
              {{ supplier.name }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Остаток</mat-label>
          <input matInput type="number" formControlName="stock_quantity" min="0">
          <span matTextSuffix>шт</span>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Минимум</mat-label>
          <input matInput type="number" formControlName="min_quantity" min="0">
          <span matTextSuffix>шт</span>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Закупочная цена</mat-label>
          <input matInput type="number" formControlName="purchase_price" min="0">
          <span matTextSuffix>₽</span>
        </mat-form-field>

        <mat-form-field>
          <mat-label>Цена продажи</mat-label>
          <input matInput type="number" formControlName="selling_price" min="0">
          <span matTextSuffix>₽</span>
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button type="button" (click)="close()">Отмена</button>
      <button mat-flat-button color="primary" type="button" (click)="save()">
        <mat-icon>save</mat-icon>
        Сохранить
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
      color: var(--color-text-primary);
    }

    .edit-dialog-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding: 22px 24px 6px;
    }

    .edit-dialog-header span {
      color: var(--color-primary);
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    .edit-dialog-header h2 {
      margin: 4px 0 0;
      color: var(--color-text-primary);
      font-size: 24px;
      font-weight: 950;
    }

    .edit-form {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      padding-top: 8px;
    }

    .span-2 {
      grid-column: 1 / -1;
    }

    mat-dialog-content {
      padding: 0 24px 8px;
    }

    mat-dialog-actions {
      padding: 10px 24px 22px;
    }

    @media (max-width: 640px) {
      .edit-form {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class InventoryItemEditDialogComponent {
  form: FormGroup;

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: InventoryItemEditDialogData,
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<InventoryItemEditDialogComponent, UpdateInventoryItemRequest | null>
  ) {
    const item = data.item;
    this.form = this.fb.group({
      name: [item.name || '', Validators.required],
      sku: [item.sku || '', Validators.required],
      item_type: [item.item_type || 'component', Validators.required],
      category_name: [item.category_name || item.category || 'Запчасти', Validators.required],
      primary_supplier_id: [item.primary_supplier_id ?? null],
      stock_quantity: [Number(item.total_stock || 0), [Validators.required, Validators.min(0)]],
      min_quantity: [Number(item.min_quantity || 0), [Validators.required, Validators.min(0)]],
      purchase_price: [Number(item.purchase_price || 0), [Validators.required, Validators.min(0)]],
      selling_price: [Number(item.selling_price || 0), [Validators.required, Validators.min(0)]],
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    this.dialogRef.close({
      name: String(value.name || '').trim(),
      sku: String(value.sku || '').trim(),
      item_type: value.item_type || 'component',
      category_name: String(value.category_name || 'Запчасти').trim(),
      primary_supplier_id: value.primary_supplier_id ?? null,
      stock_quantity: Number(value.stock_quantity || 0),
      min_quantity: Number(value.min_quantity || 0),
      purchase_price: Number(value.purchase_price || 0),
      selling_price: Number(value.selling_price || 0),
    });
  }

  close(): void {
    this.dialogRef.close(null);
  }
}

@Component({
  selector: 'app-inventory-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule
  ],
  templateUrl: './inventory-dashboard.component.html',
  styleUrl: './inventory-dashboard.component.scss',
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
export class InventoryDashboardComponent implements OnInit, AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = ['name', 'sku', 'category', 'stock_status', 'stock_level', 'price', 'actions'];
  dataSource = new MatTableDataSource<InventoryItem>();
  allItems: InventoryItem[] = [];
  suppliers: Supplier[] = [];
  filtersForm: FormGroup;

  stockAlerts: StockAlert[] = [];
  loading = false;
  lastUpdatedAt: Date | null = null;

  inventoryStats = {
    total_items: 0,
    low_stock_items: 0,
    out_of_stock_items: 0,
    total_value: 0,
    turnover_rate: 0
  };

  readonly itemTypes = [
    { value: 'component', label: 'Комплектующие' },
    { value: 'accessory', label: 'Аксессуары' },
    { value: 'consumable', label: 'Расходные материалы' },
    { value: 'tool', label: 'Инструменты' },
    { value: 'software', label: 'Программное обеспечение' },
    { value: 'service', label: 'Услуга' }
  ];

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private inventoryService: InventoryService,
    private router: Router,
    private fb: FormBuilder,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      stock_status: [''],
      category: ['']
    });
  }

  ngOnInit(): void {
    this.loadInventoryData();
    this.loadSuppliers();
    this.loadStockAlerts();
    this.loadInventoryStats();
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadInventoryData(): void {
    this.loading = true;

    this.inventoryService.getInventoryItems().subscribe({
      next: (items) => {
        this.allItems = items;
        this.applyFilters();
        this.lastUpdatedAt = new Date();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading inventory:', error);
        this.loading = false;
      }
    });
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges
      .pipe(
        debounceTime(250),
        distinctUntilChanged()
      )
      .subscribe(() => this.applyFilters());
  }

  private applyFilters(): void {
    const { search, stock_status, category } = this.filtersForm.getRawValue();
    const query = String(search || '').trim().toLowerCase();

    this.dataSource.data = this.allItems.filter(item => {
      const searchable = [
        item.name,
        item.sku,
        item.category,
        item.category_name,
        item.primary_supplier_name
      ].filter(Boolean).join(' ').toLowerCase();

      const matchesSearch = !query || searchable.includes(query);
      const matchesStatus = !stock_status || item.stock_status === stock_status;
      const matchesCategory = !category || this.getCategoryLabel(item) === category;

      return matchesSearch && matchesStatus && matchesCategory;
    });

    if (this.paginator) {
      this.paginator.firstPage();
    }
  }

  private loadStockAlerts(): void {
    this.inventoryService.getStockAlerts().subscribe({
      next: (alerts) => {
        this.stockAlerts = alerts;
      },
      error: (error) => {
        console.error('Error loading stock alerts:', error);
      }
    });
  }

  private loadInventoryStats(): void {
    this.inventoryService.getInventoryStatistics().subscribe({
      next: (stats) => {
        this.inventoryStats = stats;
      },
      error: (error) => {
        console.error('Error loading inventory stats:', error);
      }
    });
  }

  private loadSuppliers(): void {
    this.inventoryService.getSuppliers().subscribe({
      next: (suppliers) => {
        this.suppliers = suppliers;
      },
      error: (error) => {
        console.error('Error loading suppliers:', error);
      }
    });
  }

  get items(): InventoryItem[] {
    return this.dataSource.data;
  }

  get totalItems(): number {
    return this.items.length;
  }

  get totalUnits(): number {
    return this.items.reduce((sum, item) => sum + Number(item.total_stock || 0), 0);
  }

  get visibleStockValue(): number {
    return this.items.reduce((sum, item) =>
      sum + Number(item.total_stock || 0) * Number(item.purchase_price || 0), 0);
  }

  get visibleRetailValue(): number {
    return this.items.reduce((sum, item) =>
      sum + Number(item.total_stock || 0) * Number(item.selling_price || 0), 0);
  }

  get potentialMargin(): number {
    return this.visibleRetailValue - this.visibleStockValue;
  }

  get lowStockVisible(): number {
    return this.items.filter(item => item.stock_status === 'low_stock').length;
  }

  get outOfStockVisible(): number {
    return this.items.filter(item => item.stock_status === 'out_of_stock').length;
  }

  get healthyVisible(): number {
    return this.items.filter(item => item.stock_status === 'in_stock').length;
  }

  get categoryOptions(): string[] {
    return Array.from(new Set(this.allItems.map(item => this.getCategoryLabel(item)).filter(Boolean))).sort();
  }

  get hasActiveFilters(): boolean {
    return Object.values(this.filtersForm.getRawValue()).some(value =>
      value !== '' && value !== null && value !== undefined
    );
  }

  get criticalAlerts(): StockAlert[] {
    return this.stockAlerts.filter(alert => alert.alert_type === 'out_of_stock');
  }

  get warningAlerts(): StockAlert[] {
    return this.stockAlerts.filter(alert => alert.alert_type === 'low_stock');
  }

  getStockStatusClass(status: string | undefined): string {
    switch (status) {
      case 'in_stock': return 'status-in-stock';
      case 'low_stock': return 'status-low-stock';
      case 'out_of_stock': return 'status-out-stock';
      default: return 'status-out-stock';
    }
  }

  getStockStatusLabel(status: string | undefined): string {
    switch (status) {
      case 'in_stock': return 'В наличии';
      case 'low_stock': return 'Мало';
      case 'out_of_stock': return 'Нет в наличии';
      default: return 'Нет данных';
    }
  }

  getStockLevel(item: InventoryItem): number {
    const total = Number(item.total_stock || 0);
    const min = Number(item.min_quantity || 0);
    if (total <= 0) return 0;
    if (min <= 0) return 100;
    return Math.min(100, (total / (min * 2)) * 100);
  }

  getStockLevelStyle(item: InventoryItem): string {
    return `${this.getStockLevel(item)}%`;
  }

  getCategoryLabel(item: InventoryItem): string {
    return item.category_name || item.category || 'Без категории';
  }

  getStockText(item: InventoryItem): string {
    const total = Number(item.total_stock || 0);
    const min = Number(item.min_quantity || 0);
    return `${total} шт · мин ${min}`;
  }

  getAlertIcon(alertType: string): string {
    switch (alertType) {
      case 'low_stock': return 'warning';
      case 'out_of_stock': return 'error';
      case 'overstock': return 'info';
      default: return 'notification_important';
    }
  }

  getAlertColor(alertType: string): string {
    switch (alertType) {
      case 'low_stock': return 'warn';
      case 'out_of_stock': return 'warn';
      case 'overstock': return 'primary';
      default: return 'accent';
    }
  }

  formatCurrency(value: number): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  createPurchaseOrder(): void {
    this.router.navigate(['/inventory/purchase-orders/new']);
  }

  createPurchaseOrderFor(item: InventoryItem): void {
    this.router.navigate(['/inventory/purchase-orders/new'], {
      queryParams: {
        item_id: item.id
      }
    });
  }

  openItemEditor(item: InventoryItem, event?: Event): void {
    event?.stopPropagation();

    const dialogRef = this.dialog.open(InventoryItemEditDialogComponent, {
      width: '720px',
      maxWidth: 'calc(100vw - 32px)',
      panelClass: 'inventory-edit-dialog-panel',
      data: {
        item,
        suppliers: this.suppliers,
        itemTypes: this.itemTypes
      }
    });

    dialogRef.afterClosed().subscribe((payload?: UpdateInventoryItemRequest | null) => {
      if (!payload) {
        return;
      }

      this.loading = true;
      this.inventoryService.updateInventoryItem(item.id, payload).subscribe({
        next: () => {
          this.snackBar.open('Товар обновлен', 'Закрыть', { duration: 3000 });
          this.refreshInventory();
        },
        error: (error) => {
          const message = error?.error?.error || 'Не удалось обновить товар';
          this.snackBar.open(message, 'Закрыть', { duration: 4000 });
          this.loading = false;
        }
      });
    });
  }

  clearFilters(): void {
    this.filtersForm.reset({
      search: '',
      stock_status: '',
      category: ''
    });
  }

  refreshInventory(): void {
    this.loadInventoryData();
    this.loadStockAlerts();
    this.loadInventoryStats();
  }

  adjustStock(item: InventoryItem): void {
    // Открыть диалог корректировки остатков
  }

  viewItemDetails(item: InventoryItem): void {
    // Переход к детальной информации о товаре
  }

  trackById(_: number, item: InventoryItem): number {
    return item.id;
  }
}
