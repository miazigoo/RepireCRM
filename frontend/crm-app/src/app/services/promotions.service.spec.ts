import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Promotion } from '../core/models/models';
import { ApiService } from './api.service';
import { PromotionsService } from './promotions.service';

describe('PromotionsService', () => {
  let service: PromotionsService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', [
      'get',
      'post',
      'put',
      'delete',
    ]);

    TestBed.configureTestingModule({
      providers: [PromotionsService, { provide: ApiService, useValue: apiService }],
    });

    service = TestBed.inject(PromotionsService);
  });

  it('loads promotions with inactive flag only when requested', () => {
    const promotions = [{ id: 1, name: 'Лето' }] as Promotion[];
    apiService.get.and.returnValue(of(promotions));

    service.getPromotions(true).subscribe((result) => {
      expect(result).toEqual(promotions);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/promotions/campaigns', {
      include_inactive: true,
    });
  });

  it('applies promo code to order', () => {
    const discount = { id: 7, label: 'Промокод START', amount: 500 } as any;
    apiService.post.and.returnValue(of(discount));

    service.applyPromoCode(12, 'start').subscribe((result) => {
      expect(result).toEqual(discount);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/promotions/orders/12/apply-code', {
      code: 'start',
    });
  });
});
