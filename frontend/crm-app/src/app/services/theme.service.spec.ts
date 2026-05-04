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
    expect(service.getAvailableSkins().length).toBeGreaterThan(5);
    expect(service.getAppearancePresets().length).toBeGreaterThan(5);
  });

  it('applies palette, visual skin and interface style independently', () => {
    service.setTheme('forest-dark');
    service.setSkin('command-center');
    service.setStyle('compact');

    expect(service.getCurrentTheme().id).toBe('forest-dark');
    expect(service.getCurrentStyle().id).toBe('compact');
    expect(service.getCurrentSkin().id).toBe('command-center');
    expect(document.body.classList).toContain('dark-theme');
    expect(document.body.classList).toContain('forest-dark');
    expect(document.body.classList).toContain('interface-compact');
    expect(document.body.classList).toContain('skin-command-center');
    expect(document.documentElement.style.getPropertyValue('--content-padding')).toBe('18px');
  });

  it('applies complete appearance presets in one action', () => {
    service.applyAppearancePreset('premium-studio');

    expect(service.getCurrentTheme().id).toBe('coral-light');
    expect(service.getCurrentStyle().id).toBe('comfortable');
    expect(service.getCurrentSkin().id).toBe('glass-studio');
    expect(document.body.classList).toContain('skin-glass-studio');
    expect(localStorage.getItem('selectedVisualSkin')).toBe('glass-studio');
  });
});
