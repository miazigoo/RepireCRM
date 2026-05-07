import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface InventoryItem {
  id: number;
  name: string;
  sku: string;
  category: string;
  category_name?: string;
  item_type?: string;
  primary_supplier_id?: number;
  primary_supplier_name?: string;
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

export interface Supplier {
  id: number;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  is_active?: boolean;
}

export interface QuickCreateInventoryItemRequest {
  name: string;
  sku: string;
  item_type: string;
  category_name?: string;
  category_id?: number;
  purchase_price: number;
  selling_price: number;
  barcodes?: string[];
  unit?: string;
  primary_supplier_id?: number;
  description?: string;
}

export interface PurchaseOrderRequest {
  supplier_id?: number;
  supplier_name?: string;
  notes?: string;
  items: Array<{
    item_id: number;
    quantity: number;
    unit_price: number;
  }>;
}

type ListResponse<T> = T[] | { items?: T[] };

function unwrapList<T>(response: ListResponse<T>): T[] {
  return Array.isArray(response) ? response : response.items ?? [];
}

function normalizeStockStatus(item: Partial<InventoryItem>): InventoryItem['stock_status'] {
  if (item.stock_status) {
    return item.stock_status;
  }

  const totalStock = Number(item.total_stock ?? 0);
  const minQuantity = Number(item.min_quantity ?? 0);
  if (totalStock <= 0) {
    return 'out_of_stock';
  }

  return minQuantity > 0 && totalStock <= minQuantity ? 'low_stock' : 'in_stock';
}

function normalizeInventoryItem(item: Partial<InventoryItem>): InventoryItem {
  return {
    ...item,
    id: Number(item.id),
    name: item.name || '',
    sku: item.sku || '',
    category: item.category || item.category_name || 'Без категории',
    total_stock: Number(item.total_stock ?? 0),
    min_quantity: Number(item.min_quantity ?? 0),
    selling_price: Number(item.selling_price ?? 0),
    purchase_price: Number(item.purchase_price ?? 0),
    stock_status: normalizeStockStatus(item),
    last_movement_date: item.last_movement_date || '',
  };
}

@Injectable({
  providedIn: 'root'
})
export class InventoryService {
  constructor(private apiService: ApiService) {}

  getInventoryItems(): Observable<InventoryItem[]> {
    return this.apiService.get<ListResponse<InventoryItem>>('/inventory/items').pipe(
      map((response) => unwrapList(response).map(normalizeInventoryItem)),
      catchError(() => of([]))
    );
  }

  getStockAlerts(): Observable<StockAlert[]> {
    return this.apiService.get<any[]>('/inventory/stock-balances', { low_stock_only: true }).pipe(
      map((balances): StockAlert[] => balances.map((balance) => ({
        id: balance.id,
        item_name: balance.item_name,
        current_stock: balance.available_quantity,
        min_quantity: balance.min_quantity,
        shop_name: balance.shop_name,
        alert_type: balance.available_quantity <= 0 ? 'out_of_stock' : 'low_stock',
      }))),
      catchError(() => of([]))
    );
  }

  getInventoryStatistics(): Observable<InventoryStatistics> {
    return this.apiService.get<any>('/inventory/stock/dashboard').pipe(
      map((dashboard) => ({
        total_items: dashboard.totals?.total_skus ?? 0,
        low_stock_items: dashboard.totals?.low_stock_count ?? 0,
        out_of_stock_items: 0,
        total_value: 0,
        turnover_rate: 0
      })),
      catchError(() => of({
        total_items: 0,
        low_stock_items: 0,
        out_of_stock_items: 0,
        total_value: 0,
        turnover_rate: 0
      }))
    );
  }

  getSuppliers(): Observable<Supplier[]> {
    return this.apiService.get<Supplier[]>('/inventory/suppliers').pipe(
      catchError(() => of([]))
    );
  }

  quickCreateItem(data: QuickCreateInventoryItemRequest): Observable<InventoryItem> {
    return this.apiService.post<InventoryItem>('/inventory/items/quick-create', data);
  }

  createPurchaseOrder(data: PurchaseOrderRequest): Observable<any> {
    return this.apiService.post<any>('/inventory/purchase-orders', data);
  }
}
