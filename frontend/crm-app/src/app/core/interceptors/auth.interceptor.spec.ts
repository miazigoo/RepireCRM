import { HTTP_INTERCEPTORS, HttpClient, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { AuthInterceptor } from './auth.interceptor';

describe('AuthInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('can instantiate AuthService while the interceptor is registered', () => {
    expect(TestBed.inject(AuthService)).toBeTruthy();
  });

  it('adds auth and current shop headers without using AuthService', () => {
    localStorage.setItem('access_token', 'access-token');
    localStorage.setItem('current_shop_id', '12');

    http.get('/api/orders/statistics').subscribe();

    const request = httpTesting.expectOne('/api/orders/statistics');
    expect(request.request.headers.get('Authorization')).toBe('Bearer access-token');
    expect(request.request.headers.get('X-Current-Shop')).toBe('12');

    request.flush({});
  });

  it('clears the primary session on an API 401 response', () => {
    const router = TestBed.inject(Router);
    spyOn(router, 'navigate');
    localStorage.setItem('access_token', 'access-token');
    localStorage.setItem('current_shop_id', '12');

    http.get('/api/orders/statistics').subscribe({ error: () => undefined });

    const request = httpTesting.expectOne('/api/orders/statistics');
    request.flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('current_shop_id')).toBeNull();
    expect(router.navigate).toHaveBeenCalledOnceWith(['/login']);
  });
});
