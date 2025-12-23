import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Theme {
  id: string;
  name: string;
  displayName: string;
  description: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    warn: string;
    background: string;
    surface: string;
    text: {
      primary: string;
      secondary: string;
      disabled: string;
      hint: string;
    };
  };
  isDark: boolean;
  customProperties: Record<string, string>;
}

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_STORAGE_KEY = 'selectedTheme';
  private currentThemeSubject = new BehaviorSubject<Theme>(this.getDefaultTheme());

  public currentTheme$ = this.currentThemeSubject.asObservable();

  private themes: Theme[] = [
    {
      id: 'default-light',
      name: 'default-light',
      displayName: 'Светлая тема',
      description: 'Классическая светлая тема',
      isDark: false,
      colors: {
        primary: '#1976d2',
        secondary: '#424242',
        accent: '#82b1ff',
        warn: '#f44336',
        background: '#fafafa',
        surface: '#ffffff',
        text: {
          primary: 'rgba(0, 0, 0, 0.87)',
          secondary: 'rgba(0, 0, 0, 0.54)',
          disabled: 'rgba(0, 0, 0, 0.38)',
          hint: 'rgba(0, 0, 0, 0.38)'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 2px 4px rgba(0,0,0,0.1)',
        '--shadow-medium': '0 4px 8px rgba(0,0,0,0.15)',
        '--shadow-heavy': '0 8px 16px rgba(0,0,0,0.2)'
      }
    },
    {
      id: 'default-dark',
      name: 'default-dark',
      displayName: 'Темная тема',
      description: 'Современная темная тема',
      isDark: true,
      colors: {
        primary: '#90caf9',
        secondary: '#ce93d8',
        accent: '#f48fb1',
        warn: '#f48fb1',
        background: '#121212',
        surface: '#1e1e1e',
        text: {
          primary: '#ffffff',
          secondary: 'rgba(255, 255, 255, 0.7)',
          disabled: 'rgba(255, 255, 255, 0.5)',
          hint: 'rgba(255, 255, 255, 0.5)'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 2px 4px rgba(0,0,0,0.3)',
        '--shadow-medium': '0 4px 8px rgba(0,0,0,0.4)',
        '--shadow-heavy': '0 8px 16px rgba(0,0,0,0.5)'
      }
    },
    {
      id: 'corporate-blue',
      name: 'corporate-blue',
      displayName: 'Корпоративная синяя',
      description: 'Профессиональная бизнес тема',
      isDark: false,
      colors: {
        primary: '#0d47a1',
        secondary: '#1565c0',
        accent: '#42a5f5',
        warn: '#e53935',
        background: '#f5f5f5',
        surface: '#ffffff',
        text: {
          primary: 'rgba(0, 0, 0, 0.87)',
          secondary: 'rgba(0, 0, 0, 0.54)',
          disabled: 'rgba(0, 0, 0, 0.38)',
          hint: 'rgba(0, 0, 0, 0.38)'
        }
      },
      customProperties: {
        '--sidebar-width': '300px',
        '--header-height': '72px',
        '--border-radius': '4px',
        '--shadow-light': '0 2px 8px rgba(13,71,161,0.1)',
        '--shadow-medium': '0 4px 16px rgba(13,71,161,0.15)',
        '--shadow-heavy': '0 8px 24px rgba(13,71,161,0.2)'
      }
    },
    {
      id: 'green-nature',
      name: 'green-nature',
      displayName: 'Природная зеленая',
      description: 'Экологичная зеленая тема',
      isDark: false,
      colors: {
        primary: '#2e7d32',
        secondary: '#388e3c',
        accent: '#4caf50',
        warn: '#ff5722',
        background: '#f1f8e9',
        surface: '#ffffff',
        text: {
          primary: 'rgba(0, 0, 0, 0.87)',
          secondary: 'rgba(0, 0, 0, 0.54)',
          disabled: 'rgba(0, 0, 0, 0.38)',
          hint: 'rgba(0, 0, 0, 0.38)'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '12px',
        '--shadow-light': '0 2px 4px rgba(46,125,50,0.1)',
        '--shadow-medium': '0 4px 8px rgba(46,125,50,0.15)',
        '--shadow-heavy': '0 8px 16px rgba(46,125,50,0.2)'
      }
    },
    {
      id: 'high-contrast',
      name: 'high-contrast',
      displayName: 'Высокий контраст',
      description: 'Тема с высоким контрастом для лучшей доступности',
      isDark: false,
      colors: {
        primary: '#000000',
        secondary: '#424242',
        accent: '#0d47a1',
        warn: '#d32f2f',
        background: '#ffffff',
        surface: '#ffffff',
        text: {
          primary: '#000000',
          secondary: '#424242',
          disabled: '#757575',
          hint: '#757575'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '2px',
        '--shadow-light': '0 2px 4px rgba(0,0,0,0.3)',
        '--shadow-medium': '0 4px 8px rgba(0,0,0,0.4)',
        '--shadow-heavy': '0 8px 16px rgba(0,0,0,0.5)'
      }
    }
  ];

  constructor() {
    this.loadSavedTheme();
    this.applyTheme(this.currentThemeSubject.value);
  }

  getAvailableThemes(): Theme[] {
    return [...this.themes];
  }

  getCurrentTheme(): Theme {
    return this.currentThemeSubject.value;
  }

  setTheme(themeId: string): void {
    const theme = this.themes.find(t => t.id === themeId);
    if (theme) {
      this.currentThemeSubject.next(theme);
      this.applyTheme(theme);
      this.saveTheme(theme.id);
    }
  }

  private getDefaultTheme(): Theme {
    return this.themes[0]; // default-light
  }

  private loadSavedTheme(): void {
    const savedThemeId = localStorage.getItem(this.THEME_STORAGE_KEY);
    if (savedThemeId) {
      const theme = this.themes.find(t => t.id === savedThemeId);
      if (theme) {
        this.currentThemeSubject.next(theme);
      }
    }
  }

  private saveTheme(themeId: string): void {
    localStorage.setItem(this.THEME_STORAGE_KEY, themeId);
  }

  private applyTheme(theme: Theme): void {
    const root = document.documentElement;

    // Применяем CSS переменные
    Object.entries(theme.customProperties).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });

    // Применяем цветовые переменные
    root.style.setProperty('--color-primary', theme.colors.primary);
    root.style.setProperty('--color-secondary', theme.colors.secondary);
    root.style.setProperty('--color-accent', theme.colors.accent);
    root.style.setProperty('--color-warn', theme.colors.warn);
    root.style.setProperty('--color-background', theme.colors.background);
    root.style.setProperty('--color-surface', theme.colors.surface);
    root.style.setProperty('--color-text-primary', theme.colors.text.primary);
    root.style.setProperty('--color-text-secondary', theme.colors.text.secondary);

    // Добавляем/убираем класс для темной темы
    document.body.classList.toggle('dark-theme', theme.isDark);
    document.body.classList.remove(...this.themes.map(t => t.name));
    document.body.classList.add(theme.name);
  }

  // Дополнительные методы для кастомизации
  updateThemeColors(themeId: string, colors: Partial<Theme['colors']>): void {
    const themeIndex = this.themes.findIndex(t => t.id === themeId);
    if (themeIndex !== -1) {
      this.themes[themeIndex].colors = {
        ...this.themes[themeIndex].colors,
        ...colors
      };

      if (this.currentThemeSubject.value.id === themeId) {
        this.applyTheme(this.themes[themeIndex]);
      }
    }
  }

  createCustomTheme(baseThemeId: string, customizations: Partial<Theme>): Theme {
    const baseTheme = this.themes.find(t => t.id === baseThemeId);
    if (!baseTheme) throw new Error('Base theme not found');

    const customTheme: Theme = {
      ...baseTheme,
      ...customizations,
      id: customizations.id || `custom-${Date.now()}`,
      colors: { ...baseTheme.colors, ...customizations.colors },
      customProperties: { ...baseTheme.customProperties, ...customizations.customProperties }
    };

    this.themes.push(customTheme);
    return customTheme;
  }
}
