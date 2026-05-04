import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;

  beforeEach(() => {
    localStorage.clear();
    document.body.className = '';
    document.documentElement.removeAttribute('style');

    TestBed.configureTestingModule({});
    service = TestBed.inject(ThemeService);
  });

  afterEach(() => {
    localStorage.clear();
    document.body.className = '';
    document.documentElement.removeAttribute('style');
    TestBed.resetTestingModule();
  });

  it('offers a varied theme and interface style catalog', () => {
    expect(service.getAvailableThemes().length).toBeGreaterThan(9);
    expect(service.getAvailableStyles().length).toBeGreaterThan(4);
  });

  it('applies palette and interface style variables independently', () => {
    service.setTheme('forest-dark');
    service.setStyle('compact');

    expect(service.getCurrentTheme().id).toBe('forest-dark');
    expect(service.getCurrentStyle().id).toBe('compact');
    expect(document.body.classList).toContain('dark-theme');
    expect(document.body.classList).toContain('forest-dark');
    expect(document.body.classList).toContain('interface-compact');
    expect(document.documentElement.style.getPropertyValue('--content-padding')).toBe('18px');
  });
});
