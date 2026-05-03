import { CurrencyPipe } from '@angular/common';
import { LOCALE_ID } from '@angular/core';
import { appConfig } from './app.config';

describe('appConfig locale', () => {
  it('uses Russian locale so RUB is rendered as the ruble sign', () => {
    const localeProvider = appConfig.providers.find(
      (provider): provider is { provide: unknown; useValue: string } =>
        typeof provider === 'object' &&
        provider !== null &&
        'provide' in provider &&
        provider.provide === LOCALE_ID
    );

    expect(localeProvider?.useValue).toBe('ru-RU');

    const formatted = new CurrencyPipe(localeProvider!.useValue).transform(
      0,
      'RUB',
      'symbol',
      '1.0-0'
    );

    expect(formatted).toContain('₽');
    expect(formatted).not.toContain('RUB');
  });
});
