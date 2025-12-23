import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { OrdersService } from './orders.service';

describe('OrdersService', () => {
  let service: OrdersService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [OrdersService]
    });

    service = TestBed.inject(OrdersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch orders', () => {
    const mockOrders = [
      { id: 1, order_number: 'ORD-001', status: 'received' },
      { id: 2, order_number: 'ORD-002', status: 'completed' }
    ];

    service.getOrders().subscribe(orders => {
      expect(orders.length).toBe(2);
      expect(orders).toEqual(mockOrders);
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/orders`);
    expect(req.request.method).toBe('GET');
    req.flush(mockOrders);
  });
});
