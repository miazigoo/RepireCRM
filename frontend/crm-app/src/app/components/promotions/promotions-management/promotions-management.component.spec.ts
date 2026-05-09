import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { AuthService } from '../../../services/auth.service';
import { PromotionsService } from '../../../services/promotions.service';
import { PromotionsManagementComponent } from './promotions-management.component';

describe('PromotionsManagementComponent', () => {
  let fixture: ComponentFixture<PromotionsManagementComponent>;
  let component: PromotionsManagementComponent;
  let promotionsService: jasmine.SpyObj<PromotionsService>;

  beforeEach(async () => {
    promotionsService = jasmine.createSpyObj<PromotionsService>('PromotionsService', [
      'getPromotions',
      'getPromoCodes',
      'validatePromoCode',
    ]);
    promotionsService.getPromotions.and.returnValue(of([]));
    promotionsService.getPromoCodes.and.returnValue(of([]));
    promotionsService.validatePromoCode.and.returnValue(
      of({
        valid: true,
        message: 'ok',
        promotion_name: 'Старт',
        subtotal: 5000,
        discount_amount: 500,
        total_after_discount: 4500,
      }),
    );

    await TestBed.configureTestingModule({
      imports: [PromotionsManagementComponent, NoopAnimationsModule],
      providers: [
        { provide: PromotionsService, useValue: promotionsService },
        { provide: AuthService, useValue: { getAvailableShops: () => of([]) } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PromotionsManagementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads promotions and promo codes on init', () => {
    expect(promotionsService.getPromotions).toHaveBeenCalledOnceWith(true);
    expect(promotionsService.getPromoCodes).toHaveBeenCalledOnceWith(true);
  });

  it('shows quote message after promo code validation', () => {
    component.quoteForm.patchValue({ code: 'START', subtotal: 5000 });

    component.validatePromoCode();

    expect(component.quoteMessage).toContain('Старт');
    expect(promotionsService.validatePromoCode).toHaveBeenCalledWith({
      code: 'START',
      subtotal: 5000,
    });
  });
});
