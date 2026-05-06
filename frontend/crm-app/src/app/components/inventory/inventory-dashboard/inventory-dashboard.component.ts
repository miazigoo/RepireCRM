import { AfterViewInit, Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { InventoryItem, InventoryService, StockAlert } from '../../../services/inventory.service';

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
    MatProgressSpinnerModule
  ],
  templateUrl: './inventory-dashboard.component.html',
  styleUrl: './inventory-dashboard.component.scss',
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
export class InventoryDashboardComponent implements OnInit, AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = ['name', 'sku', 'category', 'stock_status', 'stock_level', 'price', 'actions'];
  dataSource = new MatTableDataSource<InventoryItem>();
  allItems: InventoryItem[] = [];
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

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private inventoryService: InventoryService,
    private router: Router,
    private fb: FormBuilder
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      stock_status: [''],
      category: ['']
    });
  }

  ngOnInit(): void {
    this.loadInventoryData();
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

  getStockStatusClass(status: string): string {
    switch (status) {
      case 'in_stock': return 'status-in-stock';
      case 'low_stock': return 'status-low-stock';
      case 'out_of_stock': return 'status-out-stock';
      default: return '';
    }
  }

  getStockStatusLabel(status: string): string {
    switch (status) {
      case 'in_stock': return 'В наличии';
      case 'low_stock': return 'Мало';
      case 'out_of_stock': return 'Нет в наличии';
      default: return status;
    }
  }

  getStockLevel(item: InventoryItem): number {
    if (item.min_quantity === 0) return 100;
    return Math.min(100, (item.total_stock / (item.min_quantity * 2)) * 100);
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
