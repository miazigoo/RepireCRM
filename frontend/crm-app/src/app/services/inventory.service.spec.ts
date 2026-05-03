import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { InventoryService } from './inventory.service';

describe('InventoryService', () => {
  let service: InventoryService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);

    TestBed.configureTestingModule({
      providers: [
        InventoryService,
        { provide: ApiService, useValue: apiService },
      ],
    });

    service = TestBed.inject(InventoryService);
  });

  it('loads stock alerts from low-stock balances', () => {
    apiService.get.and.returnValue(of([
      {
        id: 3,
        item_name: 'Дисплей iPhone 12',
        available_quantity: 0,
        min_quantity: 2,
        shop_name: 'Ремонт+ Москва Центр',
      },
    ]));

    service.getStockAlerts().subscribe((alerts) => {
      expect(alerts).toEqual([
        {
          id: 3,
          item_name: 'Дисплей iPhone 12',
          current_stock: 0,
          min_quantity: 2,
          shop_name: 'Ремонт+ Москва Центр',
          alert_type: 'out_of_stock',
        },
      ]);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/inventory/stock-balances', {
      low_stock_only: true,
    });
  });

  it('unwraps paginated inventory item responses', () => {
    const item = { id: 7, name: 'Дисплей', sku: 'LCD-1' } as any;
    apiService.get.and.returnValue(of({ items: [item], count: 1 }));

    service.getInventoryItems().subscribe((items) => {
      expect(items).toEqual([item]);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/inventory/items');
  });

  it('maps stock dashboard totals into inventory statistics', () => {
    apiService.get.and.returnValue(of({
      totals: {
        total_skus: 12,
        low_stock_count: 4,
      },
      by_shop: [],
      by_category: [],
    }));

    service.getInventoryStatistics().subscribe((statistics) => {
      expect(statistics).toEqual({
        total_items: 12,
        low_stock_items: 4,
        out_of_stock_items: 0,
        total_value: 0,
        turnover_rate: 0,
      });
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/inventory/stock/dashboard');
  });

  it('quick-creates inventory items through backend endpoint', () => {
    const item = { id: 9, name: 'Аккумулятор', sku: 'BAT-1' } as any;
    const payload = {
      name: 'Аккумулятор',
      sku: 'BAT-1',
      item_type: 'component',
      category_name: 'Запчасти',
      purchase_price: 1000,
      selling_price: 1800,
      unit: 'шт',
      barcodes: []
    };
    apiService.post.and.returnValue(of(item));

    service.quickCreateItem(payload).subscribe((result) => {
      expect(result).toEqual(item);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/inventory/items/quick-create', payload);
  });

  it('creates supplier purchase orders through backend endpoint', () => {
    const payload = {
      supplier_name: 'Основной поставщик',
      items: [{ item_id: 9, quantity: 2, unit_price: 1000 }],
      notes: ''
    };
    apiService.post.and.returnValue(of({ success: true, order_id: 4 }));

    service.createPurchaseOrder(payload).subscribe((result) => {
      expect(result).toEqual({ success: true, order_id: 4 });
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/inventory/purchase-orders', payload);
  });
});
