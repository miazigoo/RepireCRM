import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';
import { InventoryService } from '../../../services/inventory.service';

interface InventoryItem {
  id: number;
  name: string;
  sku: string;
  category: string;
  total_stock: number;
  min_quantity: number;
  selling_price: number;
  purchase_price: number;
  stock_status: 'in_stock' | 'low_stock' | 'out_of_stock';
  last_movement_date: string;
}

interface StockAlert {
  id: number;
  item_name: string;
  current_stock: number;
  min_quantity: number;
  shop_name: string;
  alert_type: 'low_stock' | 'out_of_stock' | 'overstock';
}

@Component({
  selector: 'app-inventory-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatChipsModule,
    MatMenuModule,
    MatProgressBarModule,
    MatTooltipModule,
    MatBadgeModule
  ],
  templateUrl: './inventory-dashboard.component.html',
  styleUrl: './inventory-dashboard.component.css'
})
export class InventoryDashboardComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = ['name', 'sku', 'category', 'stock_status', 'stock_level', 'price', 'actions'];
  dataSource = new MatTableDataSource<InventoryItem>();

  stockAlerts: StockAlert[] = [];
  loading = false;

  inventoryStats = {
    total_items: 0,
    low_stock_items: 0,
    out_of_stock_items: 0,
    total_value: 0,
    turnover_rate: 0
  };

  constructor(private inventoryService: InventoryService) {}

  ngOnInit(): void {
    this.loadInventoryData();
    this.loadStockAlerts();
    this.loadInventoryStats();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadInventoryData(): void {
    this.loading = true;

    this.inventoryService.getInventoryItems().subscribe({
      next: (items) => {
        this.dataSource.data = items;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading inventory:', error);
        this.loading = false;
      }
    });
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
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(value);
  }

  createPurchaseOrder(): void {
    // Переход к созданию заказа поставщику
  }

  adjustStock(item: InventoryItem): void {
    // Открыть диалог корректировки остатков
  }

  viewItemDetails(item: InventoryItem): void {
    // Переход к детальной информации о товаре
  }
}
