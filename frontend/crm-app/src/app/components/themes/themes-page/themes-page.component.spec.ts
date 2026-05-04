import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ThemesPageComponent } from './themes-page.component';

describe('ThemesPageComponent', () => {
  let fixture: ComponentFixture<ThemesPageComponent>;

  beforeEach(async () => {
    localStorage.clear();
    document.body.className = '';
    document.documentElement.removeAttribute('style');

    await TestBed.configureTestingModule({
      imports: [ThemesPageComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ThemesPageComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    localStorage.clear();
    document.body.className = '';
    document.documentElement.removeAttribute('style');
  });

  it('renders theme catalog and style presets', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.textContent).toContain('Темы');
    expect(element.textContent).toContain('Палитры');
    expect(element.textContent).toContain('Стиль');
    expect(element.querySelectorAll('.theme-card').length).toBeGreaterThan(9);
    expect(element.querySelectorAll('.style-card').length).toBeGreaterThan(4);
  });

  it('applies selected theme and style from the page', () => {
    const component = fixture.componentInstance;

    component.selectTheme('graphite-gold');
    component.selectStyle('sharp');
    fixture.detectChanges();

    expect(component.currentTheme.id).toBe('graphite-gold');
    expect(component.currentStyle.id).toBe('sharp');
    expect(document.body.classList).toContain('graphite-gold');
    expect(document.body.classList).toContain('interface-sharp');
  });
});
