import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { CustomersService } from './customers.service';

describe('CustomersService', () => {
  let service: CustomersService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get']);

    TestBed.configureTestingModule({
      providers: [
        CustomersService,
        { provide: ApiService, useValue: apiService },
      ],
    });

    service = TestBed.inject(CustomersService);
  });

  it('omits empty filter values before calling the customers API', () => {
    apiService.get.and.returnValue(of([]));

    service.getCustomers(1, 100, {
      search: '',
      source: '',
      has_orders: '' as any,
      created_from: '',
      created_to: '',
    }).subscribe();

    expect(apiService.get).toHaveBeenCalledOnceWith('/customers', {
      page: 1,
      page_size: 100,
    });
  });
});
