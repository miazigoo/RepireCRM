import { registerLocaleData } from '@angular/common';
import { ApplicationConfig, DEFAULT_CURRENCY_CODE, LOCALE_ID } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { HTTP_INTERCEPTORS } from '@angular/common/http';
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';
import { provideStoreDevtools } from '@ngrx/store-devtools';
import localeRu from '@angular/common/locales/ru';

import { routes } from './app.routes';
import { authReducer } from './store/auth/auth.reducer';
import { AuthEffects } from './store/auth/auth.effects';
import { environment } from '../environments/environment';
import { AuthInterceptor } from './core/interceptors/auth.interceptor';

registerLocaleData(localeRu);

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: LOCALE_ID, useValue: 'ru-RU' },
    { provide: DEFAULT_CURRENCY_CODE, useValue: 'RUB' },
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptorsFromDi()),
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
    provideStore({
      auth: authReducer
    }),
    provideEffects([AuthEffects]),
    provideStoreDevtools({
      maxAge: 25,
      logOnly: environment.production
    })
  ]
};
