import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface InventoryItem {
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

export interface StockAlert {
  id: number;
  item_name: string;
  current_stock: number;
  min_quantity: number;
  shop_name: string;
  alert_type: 'low_stock' | 'out_of_stock' | 'overstock';
}

export interface InventoryStatistics {
  total_items: number;
  low_stock_items: number;
  out_of_stock_items: number;
  total_value: number;
  turnover_rate: number;
}

@Injectable({
  providedIn: 'root'
})
export class InventoryService {
  constructor(private apiService: ApiService) {}

  getInventoryItems(): Observable<InventoryItem[]> {
    return this.apiService.get<InventoryItem[]>('/inventory/items').pipe(
      catchError(() => of([]))
    );
  }

  getStockAlerts(): Observable<StockAlert[]> {
    return this.apiService.get<StockAlert[]>('/inventory/alerts').pipe(
      catchError(() => of([]))
    );
  }

  getInventoryStatistics(): Observable<InventoryStatistics> {
    return this.apiService.get<InventoryStatistics>('/inventory/statistics').pipe(
      catchError(() => of({
        total_items: 0,
        low_stock_items: 0,
        out_of_stock_items: 0,
        total_value: 0,
        turnover_rate: 0
      }))
    );
  }
}
