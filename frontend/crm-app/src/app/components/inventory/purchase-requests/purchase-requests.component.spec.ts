import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import {
  InventoryService,
  PurchaseRequest,
  PurchaseRequestBatch,
  PurchaseRequestTimelineEvent,
} from '../../../services/inventory.service';
import { PurchaseRequestsComponent } from './purchase-requests.component';

describe('PurchaseRequestsComponent', () => {
  let fixture: ComponentFixture<PurchaseRequestsComponent>;
  let component: PurchaseRequestsComponent;
  let inventoryService: jasmine.SpyObj<InventoryService>;
  let router: Router;

  const batch: PurchaseRequestBatch = {
    id: 30,
    batch_number: 'PR-TEST-000001-01',
    title: 'Основной поставщик · Дисплеи',
    status: 'partially_received',
    purchase_order_id: 40,
    purchase_order_number: 'PO-TEST-000001',
    supplier_id: 7,
    supplier_name: 'Основной поставщик',
    subtotal: 6000,
    total_amount: 6000,
    created_at: '2026-05-16T08:00:00Z',
    items: [
      {
        id: 50,
        request_item_id: 20,
        item_id: 10,
        item_name: 'Дисплей iPhone 13',
        sku: 'LCD-IP13',
        quantity: 3,
        received_quantity: 1,
        remaining_quantity: 2,
        unit_price: 2000,
        total_price: 6000,
      },
    ],
  };

  const request: PurchaseRequest = {
    id: 1,
    request_number: 'PR-TEST-000001',
    status: 'partially_received',
    priority: 'high',
    due_date: '2026-06-01',
    subtotal: 6000,
    total_amount: 6000,
    notes: 'Нужно до пятницы',
    shop_id: 1,
    shop_name: 'Основной склад',
    created_by_id: 2,
    created_by_name: 'Директор',
    created_at: '2026-05-16T07:00:00Z',
    updated_at: '2026-05-16T08:30:00Z',
    items_count: 1,
    batches_count: 1,
    items: [
      {
        id: 20,
        item_id: 10,
        item_name: 'Дисплей iPhone 13',
        sku: 'LCD-IP13',
        category_name: 'Дисплеи',
        supplier_id: 7,
        supplier_name: 'Основной поставщик',
        requested_quantity: 3,
        approved_quantity: 3,
        received_quantity: 1,
        unit_price: 2000,
        total_price: 6000,
      },
    ],
    batches: [batch],
  };

  const timeline: PurchaseRequestTimelineEvent[] = [
    {
      id: 100,
      event_type: 'audit',
      action: 'received',
      message: 'Принята поставка по документу PR-TEST-000001-01',
      batch_id: 30,
      batch_number: 'PR-TEST-000001-01',
      actor_name: 'Директор',
      created_at: '2026-05-16T08:30:00Z',
    },
  ];

  beforeEach(async () => {
    inventoryService = jasmine.createSpyObj<InventoryService>('InventoryService', [
      'getSuppliers',
      'getProductGroups',
      'getPurchaseRequests',
      'getPurchaseRequest',
      'getPurchaseRequestTimeline',
      'setPurchaseRequestStatus',
      'splitPurchaseRequest',
      'updatePurchaseRequestItem',
      'createPurchaseRequestBatch',
      'createPurchaseOrderFromBatch',
      'receivePurchaseRequestBatch',
      'receivePurchaseRequestBatchFull',
      'downloadPurchaseRequestPdf',
      'downloadPurchaseRequestBatchPdf',
    ]);
    inventoryService.getSuppliers.and.returnValue(of([{ id: 7, name: 'Основной поставщик' }]));
    inventoryService.getProductGroups.and.returnValue(of([{ id: 3, name: 'Дисплеи' }]));
    inventoryService.getPurchaseRequests.and.returnValue(of([request]));
    inventoryService.getPurchaseRequest.and.returnValue(of(request));
    inventoryService.getPurchaseRequestTimeline.and.returnValue(of(timeline));
    inventoryService.receivePurchaseRequestBatch.and.returnValue(of({ success: true }));

    await TestBed.configureTestingModule({
      imports: [PurchaseRequestsComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: InventoryService, useValue: inventoryService },
        { provide: MatSnackBar, useValue: { open: jasmine.createSpy('open') } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PurchaseRequestsComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('renders purchase request details, batch receive state and timeline', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Заявки поставщикам');
    expect(text).toContain('PR-TEST-000001');
    expect(text).toContain('Основной поставщик · Дисплеи');
    expect(text).toContain('принято 1');
    expect(text).toContain('осталось 2');
    expect(text).toContain('Принята поставка');
  });

  it('loads requests with selected filters', () => {
    inventoryService.getPurchaseRequests.calls.reset();
    component.filters = {
      status: 'sent',
      supplierId: 7,
      dueFrom: '2026-06-01',
      dueTo: '2026-06-10',
      search: 'LCD',
    };

    component.loadRequests();

    expect(inventoryService.getPurchaseRequests).toHaveBeenCalledOnceWith({
      status: 'sent',
      supplier_id: 7,
      due_from: '2026-06-01',
      due_to: '2026-06-10',
      search: 'LCD',
    });
  });

  it('submits partial batch receiving payload from selected quantities', () => {
    component.selectedRequest = request;
    component.setReceiveQuantity(batch.items[0], 2);

    component.receiveBatchPartial(batch);

    expect(inventoryService.receivePurchaseRequestBatch).toHaveBeenCalledOnceWith(
      1,
      30,
      [{ batch_item_id: 50, received_quantity: 2 }]
    );
  });

  it('navigates to request creation page', () => {
    const navigate = spyOn(router, 'navigate');

    component.createRequest();

    expect(navigate).toHaveBeenCalledWith(['/inventory/purchase-requests/new']);
  });

  it('does not allow review or split actions for terminal requests', () => {
    component.selectedRequest = {
      ...request,
      status: 'rejected',
      batches: [],
    };

    component.approve();
    component.split('supplier');

    expect(inventoryService.setPurchaseRequestStatus).not.toHaveBeenCalled();
    expect(inventoryService.splitPurchaseRequest).not.toHaveBeenCalled();
    expect(component.canReviewSelected()).toBeFalse();
    expect(component.canSplitSelected()).toBeFalse();
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});
