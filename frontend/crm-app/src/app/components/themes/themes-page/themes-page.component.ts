import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import {
  InterfaceStyle,
  Theme,
  ThemeColorOverrides,
  ThemeService,
  VisualSkin
} from '../../../services/theme.service';

type ThemeModeFilter = 'all' | 'light' | 'dark';
type PaletteColorKey = keyof Omit<Theme['colors'], 'text'>;

interface PaletteSlot {
  key: PaletteColorKey;
  label: string;
}

@Component({
  selector: 'app-themes-page',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonToggleModule
  ],
  templateUrl: './themes-page.component.html',
  styleUrl: './themes-page.component.scss'
})
export class ThemesPageComponent implements OnInit {
  themes: Theme[] = [];
  styles: InterfaceStyle[] = [];
  skins: VisualSkin[] = [];
  currentTheme!: Theme;
  currentStyle!: InterfaceStyle;
  currentSkin!: VisualSkin;
  modeFilter: ThemeModeFilter = 'all';
  readonly paletteSlots: PaletteSlot[] = [
    { key: 'primary', label: 'Основной цвет' },
    { key: 'accent', label: 'Акцент' },
    { key: 'secondary', label: 'Вторичный цвет' },
    { key: 'warn', label: 'Цвет ошибок' },
    { key: 'background', label: 'Фон' },
    { key: 'surface', label: 'Поверхность' }
  ];

  constructor(private themeService: ThemeService) {}

  ngOnInit(): void {
    this.themes = this.themeService.getAvailableThemes();
    this.styles = this.themeService.getAvailableStyles();
    this.skins = this.themeService.getAvailableSkins();
    this.currentTheme = this.themeService.getCurrentTheme();
    this.currentStyle = this.themeService.getCurrentStyle();
    this.currentSkin = this.themeService.getCurrentSkin();

    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });

    this.themeService.currentStyle$.subscribe(style => {
      this.currentStyle = style;
    });

    this.themeService.currentSkin$.subscribe(skin => {
      this.currentSkin = skin;
    });
  }

  get filteredThemes(): Theme[] {
    if (this.modeFilter === 'light') {
      return this.themes.filter(theme => !theme.isDark);
    }

    if (this.modeFilter === 'dark') {
      return this.themes.filter(theme => theme.isDark);
    }

    return this.themes;
  }

  setModeFilter(filter: ThemeModeFilter): void {
    this.modeFilter = filter;
  }

  selectTheme(themeId: string): void {
    this.themeService.setTheme(themeId);
  }

  selectThemeFromKeyboard(event: KeyboardEvent, themeId: string): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.selectTheme(themeId);
    }
  }

  getThemeColor(theme: Theme, key: PaletteColorKey): string {
    return theme.colors[key];
  }

  updateThemeColor(theme: Theme, key: PaletteColorKey, event: Event): void {
    event.stopPropagation();
    const input = event.target as HTMLInputElement;
    const color = input.value;

    if (!color) {
      return;
    }

    this.themeService.setTheme(theme.id);
    this.themeService.updateThemeColors(theme.id, {
      [key]: color
    } as ThemeColorOverrides);
    this.themes = this.themeService.getAvailableThemes();
    this.currentTheme = this.themeService.getCurrentTheme();
  }

  selectStyle(styleId: string): void {
    this.themeService.setStyle(styleId);
  }

  selectSkin(skinId: string): void {
    this.themeService.setSkin(skinId);
  }

  trackById(_: number, item: Theme | InterfaceStyle | VisualSkin): string {
    return item.id;
  }

  getThemePreviewStyles(theme: Theme): Record<string, string> {
    return {
      '--preview-primary': theme.colors.primary,
      '--preview-secondary': theme.colors.secondary,
      '--preview-accent': theme.colors.accent,
      '--preview-background': theme.colors.background,
      '--preview-surface': theme.colors.surface,
      '--preview-surface-strong':
        theme.customProperties['--color-surface-strong'] || theme.colors.surface,
      '--preview-border':
        theme.customProperties['--color-border'] || theme.colors.secondary,
      '--preview-text': theme.colors.text.primary,
      '--preview-muted': theme.colors.text.secondary
    };
  }

}
