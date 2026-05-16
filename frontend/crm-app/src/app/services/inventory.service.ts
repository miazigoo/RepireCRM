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
  procurement_group_id?: number;
  procurement_group_name?: string;
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

export interface InventoryProductGroup {
  id: number;
  name: string;
  description?: string;
  is_active?: boolean;
}

export interface QuickCreateInventoryItemRequest {
  name: string;
  sku: string;
  item_type: string;
  category_name?: string;
  category_id?: number;
  procurement_group_id?: number;
  procurement_group_name?: string;
  purchase_price: number;
  selling_price: number;
  barcodes?: string[];
  unit?: string;
  primary_supplier_id?: number;
  description?: string;
}

export interface UpdateInventoryItemRequest {
  name?: string;
  sku?: string;
  item_type?: string;
  category_name?: string;
  category_id?: number;
  procurement_group_id?: number | null;
  procurement_group_name?: string;
  primary_supplier_id?: number | null;
  purchase_price?: number;
  selling_price?: number;
  stock_quantity?: number;
  min_quantity?: number;
  unit?: string;
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

export interface PurchaseRequestItem {
  id: number;
  item_id: number;
  item_name: string;
  sku: string;
  category_name?: string;
  supplier_id?: number | null;
  supplier_name?: string | null;
  procurement_group_id?: number | null;
  procurement_group_name?: string | null;
  requested_quantity: number;
  approved_quantity: number;
  received_quantity: number;
  unit_price: number;
  total_price: number;
  notes?: string | null;
}

export interface PurchaseRequestBatchItem {
  id: number;
  request_item_id: number;
  item_id: number;
  item_name: string;
  sku: string;
  quantity: number;
  received_quantity: number;
  remaining_quantity: number;
  unit_price: number;
  total_price: number;
  notes?: string | null;
}

export interface PurchaseRequestBatch {
  id: number;
  batch_number: string;
  title: string;
  status: string;
  purchase_order_id?: number | null;
  purchase_order_number?: string | null;
  supplier_id?: number | null;
  supplier_name?: string | null;
  procurement_group_id?: number | null;
  procurement_group_name?: string | null;
  subtotal: number;
  total_amount: number;
  notes?: string | null;
  created_at: string;
  items: PurchaseRequestBatchItem[];
}

export interface PurchaseRequest {
  id: number;
  request_number: string;
  status: string;
  priority: string;
  due_date?: string | null;
  subtotal: number;
  total_amount: number;
  notes?: string | null;
  rejection_reason?: string | null;
  shop_id: number;
  shop_name: string;
  created_by_id: number;
  created_by_name: string;
  reviewed_by_id?: number | null;
  reviewed_by_name?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  items_count: number;
  batches_count: number;
  items: PurchaseRequestItem[];
  batches: PurchaseRequestBatch[];
}

export interface PurchaseRequestCreate {
  priority?: string;
  due_date?: string | null;
  notes?: string;
  as_draft?: boolean;
  items: Array<{
    item_id: number;
    quantity: number;
    unit_price?: number;
    supplier_id?: number | null;
    supplier_name?: string;
    procurement_group_id?: number | null;
    procurement_group_name?: string;
    notes?: string;
  }>;
}

export interface PurchaseRequestItemUpdate {
  requested_quantity?: number;
  approved_quantity?: number;
  unit_price?: number;
  supplier_id?: number | null;
  supplier_name?: string;
  procurement_group_id?: number | null;
  procurement_group_name?: string;
  notes?: string;
}

export interface PurchaseRequestBatchCreate {
  supplier_id?: number | null;
  supplier_name?: string;
  procurement_group_id?: number | null;
  procurement_group_name?: string;
  title?: string;
  notes?: string;
  items: Array<{
    request_item_id: number;
    quantity: number;
    unit_price?: number;
    notes?: string;
  }>;
}

export interface PurchaseRequestTimelineEvent {
  id: number;
  event_type: 'audit' | 'request_status' | 'batch_status' | string;
  action?: string | null;
  message: string;
  old_status?: string | null;
  new_status?: string | null;
  batch_id?: number | null;
  batch_number?: string | null;
  actor_name?: string | null;
  changes?: Record<string, unknown> | null;
  created_at: string;
}

export interface PurchaseRequestFilters {
  status?: string | null;
  supplier_id?: number | null;
  due_from?: string | null;
  due_to?: string | null;
  search?: string | null;
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
    procurement_group_id: item.procurement_group_id,
    procurement_group_name: item.procurement_group_name || '',
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

  getProductGroups(): Observable<InventoryProductGroup[]> {
    return this.apiService.get<InventoryProductGroup[]>('/inventory/product-groups').pipe(
      catchError(() => of([]))
    );
  }

  quickCreateItem(data: QuickCreateInventoryItemRequest): Observable<InventoryItem> {
    return this.apiService.post<InventoryItem>('/inventory/items/quick-create', data);
  }

  updateInventoryItem(id: number, data: UpdateInventoryItemRequest): Observable<InventoryItem> {
    return this.apiService.put<InventoryItem>(`/inventory/items/${id}`, data).pipe(
      map(normalizeInventoryItem)
    );
  }

  createPurchaseOrder(data: PurchaseOrderRequest): Observable<any> {
    return this.apiService.post<any>('/inventory/purchase-orders', data);
  }

  getPurchaseRequests(filters: PurchaseRequestFilters = {}): Observable<PurchaseRequest[]> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== null && value !== undefined && value !== '')
    );
    return this.apiService.get<ListResponse<PurchaseRequest>>('/inventory/purchase-requests', params).pipe(
      map((response) => unwrapList(response)),
      catchError(() => of([]))
    );
  }

  getPurchaseRequest(id: number): Observable<PurchaseRequest> {
    return this.apiService.get<PurchaseRequest>(`/inventory/purchase-requests/${id}`);
  }

  createPurchaseRequest(data: PurchaseRequestCreate): Observable<PurchaseRequest> {
    return this.apiService.post<PurchaseRequest>('/inventory/purchase-requests', data);
  }

  getPurchaseRequestTimeline(id: number): Observable<PurchaseRequestTimelineEvent[]> {
    return this.apiService.get<PurchaseRequestTimelineEvent[]>(`/inventory/purchase-requests/${id}/timeline`).pipe(
      catchError(() => of([]))
    );
  }

  updatePurchaseRequestItem(
    requestId: number,
    itemId: number,
    data: PurchaseRequestItemUpdate
  ): Observable<PurchaseRequestItem> {
    return this.apiService.patch<PurchaseRequestItem>(
      `/inventory/purchase-requests/${requestId}/items/${itemId}`,
      data
    );
  }

  setPurchaseRequestStatus(id: number, status: string, reason?: string): Observable<PurchaseRequest> {
    return this.apiService.post<PurchaseRequest>(`/inventory/purchase-requests/${id}/status`, {
      status,
      reason: reason || ''
    });
  }

  splitPurchaseRequest(id: number, mode: 'supplier' | 'group' | 'supplier_group'): Observable<PurchaseRequestBatch[]> {
    return this.apiService.post<PurchaseRequestBatch[]>(`/inventory/purchase-requests/${id}/split`, {
      mode,
      rebuild: true
    });
  }

  createPurchaseRequestBatch(requestId: number, data: PurchaseRequestBatchCreate): Observable<PurchaseRequestBatch> {
    return this.apiService.post<PurchaseRequestBatch>(
      `/inventory/purchase-requests/${requestId}/batches`,
      data
    );
  }

  createPurchaseOrderFromBatch(requestId: number, batchId: number): Observable<any> {
    return this.apiService.post<any>(
      `/inventory/purchase-requests/${requestId}/batches/${batchId}/purchase-order`,
      {}
    );
  }

  receivePurchaseRequestBatchFull(requestId: number, batchId: number): Observable<any> {
    return this.apiService.post<any>(
      `/inventory/purchase-requests/${requestId}/batches/${batchId}/receive-full`,
      {}
    );
  }

  receivePurchaseRequestBatch(
    requestId: number,
    batchId: number,
    items: Array<{ batch_item_id: number; received_quantity: number }>
  ): Observable<any> {
    return this.apiService.post<any>(
      `/inventory/purchase-requests/${requestId}/batches/${batchId}/receive`,
      { items }
    );
  }

  downloadPurchaseRequestPdf(id: number): Observable<Blob> {
    return this.apiService.getBlob(`/inventory/purchase-requests/${id}/pdf`);
  }

  downloadPurchaseRequestBatchPdf(requestId: number, batchId: number): Observable<Blob> {
    return this.apiService.getBlob(`/inventory/purchase-requests/${requestId}/batches/${batchId}/pdf`);
  }
}
