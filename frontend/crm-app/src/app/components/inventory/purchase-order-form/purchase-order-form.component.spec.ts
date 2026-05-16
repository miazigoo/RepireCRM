import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { InventoryItem, InventoryService, PurchaseRequest } from '../../../services/inventory.service';
import { PurchaseOrderFormComponent } from './purchase-order-form.component';

describe('PurchaseOrderFormComponent', () => {
  let fixture: ComponentFixture<PurchaseOrderFormComponent>;
  let component: PurchaseOrderFormComponent;
  let inventoryService: jasmine.SpyObj<InventoryService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let router: Router;

  const item: InventoryItem = {
    id: 10,
    name: 'Дисплей iPhone 13',
    sku: 'LCD-IP13',
    category: 'Дисплеи',
    category_name: 'Дисплеи',
    procurement_group_id: 3,
    procurement_group_name: 'Экраны',
    primary_supplier_id: 7,
    primary_supplier_name: 'Основной поставщик',
    total_stock: 1,
    min_quantity: 3,
    selling_price: 4500,
    purchase_price: 2000,
    stock_status: 'low_stock',
    last_movement_date: '2026-05-16T08:00:00Z',
  };

  const createdRequest: PurchaseRequest = {
    id: 1,
    request_number: 'PR-TEST-000001',
    status: 'submitted',
    priority: 'high',
    due_date: '2026-06-01',
    subtotal: 4000,
    total_amount: 4000,
    shop_id: 1,
    shop_name: 'Основной склад',
    created_by_id: 2,
    created_by_name: 'Склад',
    created_at: '2026-05-16T08:00:00Z',
    updated_at: '2026-05-16T08:00:00Z',
    items_count: 1,
    batches_count: 0,
    items: [],
    batches: [],
  };

  beforeEach(async () => {
    inventoryService = jasmine.createSpyObj<InventoryService>('InventoryService', [
      'getSuppliers',
      'getProductGroups',
      'getInventoryItems',
      'createPurchaseRequest',
    ]);
    inventoryService.getSuppliers.and.returnValue(of([{ id: 7, name: 'Основной поставщик' }]));
    inventoryService.getProductGroups.and.returnValue(of([{ id: 3, name: 'Экраны' }]));
    inventoryService.getInventoryItems.and.returnValue(of([item]));
    inventoryService.createPurchaseRequest.and.returnValue(of(createdRequest));
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [PurchaseOrderFormComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ item_id: '10' }) } },
        },
        { provide: InventoryService, useValue: inventoryService },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PurchaseOrderFormComponent);
    component = fixture.componentInstance;
    (component as any).snackBar = snackBar;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('preselects item procurement defaults from query param', () => {
    const line = component.lines.at(0);

    expect(line.get('item_id')?.value).toBe(10);
    expect(line.get('supplier_id')?.value).toBe(7);
    expect(line.get('procurement_group_name')?.value).toBe('Экраны');
    expect(line.get('unit_price')?.value).toBe(2000);
  });

  it('clears selected supplier when a new supplier name is typed', () => {
    const line = component.lines.at(0);
    line.patchValue({ supplier_id: 7, supplier_name: 'Новый поставщик' });

    component.onSupplierNameInput(0);

    expect(line.get('supplier_id')?.value).toBeNull();
  });

  it('creates submitted purchase request with normalized payload', () => {
    const navigate = spyOn(router, 'navigate');
    component.form.patchValue({
      priority: 'high',
      due_date: '2026-06-01',
      notes: 'Срочно пополнить склад',
    });
    component.lines.at(0).patchValue({
      quantity: 2,
      supplier_id: null,
      supplier_name: 'Новый поставщик',
      notes: 'Проверить ревизию',
    });

    component.save(false);

    expect(inventoryService.createPurchaseRequest).toHaveBeenCalledOnceWith({
      priority: 'high',
      due_date: '2026-06-01',
      notes: 'Срочно пополнить склад',
      as_draft: false,
      items: [
        {
          item_id: 10,
          quantity: 2,
          unit_price: 2000,
          supplier_id: null,
          supplier_name: 'Новый поставщик',
          procurement_group_name: 'Экраны',
          notes: 'Проверить ревизию',
        },
      ],
    });
    expect(navigate).toHaveBeenCalledWith(['/inventory/purchase-requests']);
  });

  it('blocks duplicate item rows before sending request to API', () => {
    inventoryService.createPurchaseRequest.calls.reset();
    component.lines.clear();
    component.addLine();
    component.addLine();
    component.lines.controls.forEach((line) => {
      line.patchValue({
        item_id: 10,
        quantity: 1,
        unit_price: 2000,
      });
    });
    expect(component.lines.length).toBe(2);
    expect(component.lines.controls.map((line) => line.get('item_id')?.value)).toEqual([10, 10]);

    component.save(false);

    expect(inventoryService.createPurchaseRequest).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Товар Дисплей iPhone 13 уже есть в заявке',
      'Закрыть',
      { duration: 3500 }
    );
  });
});
