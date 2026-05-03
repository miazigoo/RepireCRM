import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { InventoryService } from './inventory.service';

describe('InventoryService', () => {
  let service: InventoryService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get']);

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
});
