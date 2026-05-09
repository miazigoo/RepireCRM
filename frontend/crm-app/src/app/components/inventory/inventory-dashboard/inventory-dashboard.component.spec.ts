import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import {
  InventoryItem,
  InventoryService,
  StockAlert,
} from '../../../services/inventory.service';
import { InventoryDashboardComponent } from './inventory-dashboard.component';

describe('InventoryDashboardComponent', () => {
  let fixture: ComponentFixture<InventoryDashboardComponent>;
  let component: InventoryDashboardComponent;
  let inventoryService: jasmine.SpyObj<InventoryService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let router: Router;

  const items: InventoryItem[] = [
    {
      id: 1,
      name: 'Чехол MagSafe',
      sku: 'CASE-01',
      category: 'Аксессуары',
      category_name: 'Аксессуары',
      primary_supplier_name: 'Склад Москва',
      total_stock: 0,
      min_quantity: 2,
      selling_price: 1500,
      purchase_price: 450,
      stock_status: 'out_of_stock',
      last_movement_date: '2026-05-03T21:26:00Z',
    },
    {
      id: 2,
      name: 'Аккумулятор iPhone 12',
      sku: 'BAT-12',
      category: 'Запчасти',
      total_stock: 6,
      min_quantity: 2,
      selling_price: 3900,
      purchase_price: 1600,
      stock_status: 'in_stock',
      last_movement_date: '2026-05-01T12:00:00Z',
    },
  ];

  const alerts: StockAlert[] = [
    {
      id: 3,
      item_name: 'Чехол MagSafe',
      shop_name: 'Основной склад',
      current_stock: 0,
      min_quantity: 2,
      alert_type: 'out_of_stock',
    },
  ];

  beforeEach(async () => {
    inventoryService = jasmine.createSpyObj<InventoryService>('InventoryService', [
      'getInventoryItems',
      'getSuppliers',
      'getStockAlerts',
      'getInventoryStatistics',
      'updateInventoryItem',
    ]);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    inventoryService.getInventoryItems.and.returnValue(of(items));
    inventoryService.getSuppliers.and.returnValue(of([
      { id: 4, name: 'Склад Москва' },
    ]));
    inventoryService.getStockAlerts.and.returnValue(of(alerts));
    inventoryService.getInventoryStatistics.and.returnValue(of({
      total_items: 2,
      low_stock_items: 0,
      out_of_stock_items: 1,
      total_value: 9600,
      turnover_rate: 0,
    }));

    await TestBed.configureTestingModule({
      imports: [InventoryDashboardComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: InventoryService, useValue: inventoryService },
        { provide: MatDialog, useValue: dialog },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(InventoryDashboardComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('renders the redesigned inventory workspace with metrics and alerts', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Складской контур');
    expect(text).toContain('Товары на складе');
    expect(text).toContain('Чехол MagSafe');
    expect(text).toContain('9 600 ₽');
    expect(text).toContain('Контроль');
    expect(text).not.toContain('RUB');
  });

  it('calculates stock metrics for the visible selection', () => {
    expect(component.totalItems).toBe(2);
    expect(component.totalUnits).toBe(6);
    expect(component.visibleStockValue).toBe(9600);
    expect(component.visibleRetailValue).toBe(23400);
    expect(component.potentialMargin).toBe(13800);
    expect(component.outOfStockVisible).toBe(1);
  });

  it('filters inventory by search, status and category', fakeAsync(() => {
    component.filtersForm.patchValue({
      search: 'чехол',
      stock_status: 'out_of_stock',
      category: 'Аксессуары',
    });
    tick(250);
    fixture.detectChanges();

    expect(component.totalItems).toBe(1);
    expect(component.items[0].sku).toBe('CASE-01');
  }));

  it('navigates to supplier order creation from page and item actions', () => {
    const navigate = spyOn(router, 'navigate');

    component.createPurchaseOrder();
    component.createPurchaseOrderFor(items[1]);

    expect(navigate).toHaveBeenCalledWith(['/inventory/purchase-orders/new']);
    expect(navigate).toHaveBeenCalledWith(['/inventory/purchase-orders/new'], {
      queryParams: { item_id: 2 },
    });
  });

  it('opens item edit dialog and persists inventory changes', () => {
    dialog.open.and.returnValue({
      afterClosed: () => of({
        name: 'Аккумулятор iPhone 12 Pro',
        sku: 'BAT-12-PRO',
        item_type: 'component',
        category_name: 'Запчасти',
        primary_supplier_id: 4,
        stock_quantity: 8,
        min_quantity: 2,
        purchase_price: 1700,
        selling_price: 4200,
      }),
    } as any);
    inventoryService.updateInventoryItem.and.returnValue(of({
      ...items[1],
      name: 'Аккумулятор iPhone 12 Pro',
      total_stock: 8,
      selling_price: 4200,
    }));
    (component as any).dialog = dialog;
    (component as any).snackBar = snackBar;

    component.openItemEditor(items[1]);

    expect(dialog.open).toHaveBeenCalled();
    expect(inventoryService.updateInventoryItem).toHaveBeenCalledOnceWith(2, jasmine.objectContaining({
      name: 'Аккумулятор iPhone 12 Pro',
      primary_supplier_id: 4,
      stock_quantity: 8,
    }));
    expect(snackBar.open).toHaveBeenCalledWith('Товар обновлен', 'Закрыть', { duration: 3000 });
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});
