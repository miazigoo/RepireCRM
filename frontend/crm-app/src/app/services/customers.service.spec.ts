import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { CustomersService } from './customers.service';

describe('CustomersService', () => {
  let service: CustomersService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);

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

  it('unwraps paginated customer responses', () => {
    const customer = {
      id: 1,
      first_name: 'Петр',
      last_name: 'Петров',
      phone: '+79161234567',
    } as any;
    apiService.get.and.returnValue(of({ items: [customer], count: 1 }));

    service.getCustomers().subscribe((customers) => {
      expect(customers).toEqual([customer]);
    });
  });

  it('creates customers using trailing slash endpoint', () => {
    const payload = {
      first_name: 'Анна',
      last_name: 'Иванова',
      phone: '+79990000000',
    };
    const customer = { id: 2, ...payload } as any;
    apiService.post.and.returnValue(of(customer));

    service.createCustomer(payload).subscribe((result) => {
      expect(result).toEqual(customer);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/customers/', payload);
  });
});
