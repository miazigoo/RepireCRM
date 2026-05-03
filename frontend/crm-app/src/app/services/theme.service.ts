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
  private currentThemeSubject!: BehaviorSubject<Theme>;

  public currentTheme$!: Observable<Theme>;

  private themes: Theme[] = [
    {
      id: 'default-light',
      name: 'default-light',
      displayName: 'Светлая рабочая',
      description: 'Светлая тема для ежедневной приемки',
      isDark: false,
      colors: {
        primary: '#0f62fe',
        secondary: '#334155',
        accent: '#0f766e',
        warn: '#dc2626',
        background: '#f4f7fb',
        surface: '#ffffff',
        text: {
          primary: '#111827',
          secondary: '#526071',
          disabled: '#8a94a6',
          hint: '#8a94a6'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 34px rgba(15,23,42,0.08)',
        '--shadow-medium': '0 18px 48px rgba(15,23,42,0.12)',
        '--shadow-heavy': '0 24px 64px rgba(15,23,42,0.18)',
        '--color-border': '#d9e2ef',
        '--color-surface-strong': '#eef3f9',
        '--color-toolbar': 'rgba(255,255,255,0.96)'
      }
    },
    {
      id: 'default-dark',
      name: 'default-dark',
      displayName: 'Темная графитовая',
      description: 'Темная тема с высоким контрастом',
      isDark: true,
      colors: {
        primary: '#60a5fa',
        secondary: '#94a3b8',
        accent: '#2dd4bf',
        warn: '#fb7185',
        background: '#0d1117',
        surface: '#151b23',
        text: {
          primary: '#f8fafc',
          secondary: '#cbd5e1',
          disabled: '#64748b',
          hint: '#94a3b8'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.28)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.38)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.48)',
        '--color-border': '#2b3544',
        '--color-surface-strong': '#1f2937',
        '--color-toolbar': 'rgba(21,27,35,0.96)'
      }
    },
    {
      id: 'steel-light',
      name: 'steel-light',
      displayName: 'Стальная светлая',
      description: 'Холодная светлая тема для таблиц',
      isDark: false,
      colors: {
        primary: '#2563eb',
        secondary: '#475569',
        accent: '#0891b2',
        warn: '#e11d48',
        background: '#eef2f7',
        surface: '#ffffff',
        text: {
          primary: '#0f172a',
          secondary: '#475569',
          disabled: '#94a3b8',
          hint: '#94a3b8'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 32px rgba(30,41,59,0.10)',
        '--shadow-medium': '0 18px 48px rgba(30,41,59,0.14)',
        '--shadow-heavy': '0 26px 70px rgba(30,41,59,0.20)',
        '--color-border': '#cbd5e1',
        '--color-surface-strong': '#e8eef6',
        '--color-toolbar': 'rgba(248,250,252,0.96)'
      }
    },
    {
      id: 'warm-light',
      name: 'warm-light',
      displayName: 'Теплая светлая',
      description: 'Мягкая светлая тема без холодного серого',
      isDark: false,
      colors: {
        primary: '#b45309',
        secondary: '#365314',
        accent: '#15803d',
        warn: '#be123c',
        background: '#faf7f0',
        surface: '#fffdf8',
        text: {
          primary: '#1f2937',
          secondary: '#5b6472',
          disabled: '#9ca3af',
          hint: '#9ca3af'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 32px rgba(120,53,15,0.09)',
        '--shadow-medium': '0 18px 48px rgba(120,53,15,0.13)',
        '--shadow-heavy': '0 26px 70px rgba(120,53,15,0.18)',
        '--color-border': '#e4d7c3',
        '--color-surface-strong': '#f3eadc',
        '--color-toolbar': 'rgba(255,253,248,0.96)'
      }
    },
    {
      id: 'teal-dark',
      name: 'teal-dark',
      displayName: 'Темная бирюзовая',
      description: 'Темная тема с бирюзовым акцентом',
      isDark: true,
      colors: {
        primary: '#5eead4',
        secondary: '#93c5fd',
        accent: '#facc15',
        warn: '#fb7185',
        background: '#071312',
        surface: '#10201f',
        text: {
          primary: '#ecfeff',
          secondary: '#b6d7d4',
          disabled: '#68827f',
          hint: '#8fb4b0'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.30)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.40)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.50)',
        '--color-border': '#24403d',
        '--color-surface-strong': '#17302e',
        '--color-toolbar': 'rgba(16,32,31,0.96)'
      }
    },
    {
      id: 'berry-dark',
      name: 'berry-dark',
      displayName: 'Темная ягодная',
      description: 'Темная тема с теплым акцентом',
      isDark: true,
      colors: {
        primary: '#f472b6',
        secondary: '#c4b5fd',
        accent: '#fbbf24',
        warn: '#fb7185',
        background: '#160d14',
        surface: '#241522',
        text: {
          primary: '#fff7fb',
          secondary: '#ead2df',
          disabled: '#8c7081',
          hint: '#b999aa'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.30)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.40)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.50)',
        '--color-border': '#43283e',
        '--color-surface-strong': '#321f2f',
        '--color-toolbar': 'rgba(36,21,34,0.96)'
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
        '--shadow-heavy': '0 8px 16px rgba(0,0,0,0.5)',
        '--color-border': '#000000',
        '--color-surface-strong': '#f3f4f6',
        '--color-toolbar': '#ffffff'
      }
    }
  ];

  constructor() {
    this.currentThemeSubject = new BehaviorSubject<Theme>(this.getDefaultTheme());
    this.currentTheme$ = this.currentThemeSubject.asObservable();
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
    root.style.setProperty('--color-text-disabled', theme.colors.text.disabled);
    const defaults: Record<string, string> = {
      '--color-border': theme.isDark ? '#334155' : '#d8e0ea',
      '--color-surface-strong': theme.isDark ? '#223047' : '#f3f6fb',
      '--color-primary-soft': theme.isDark ? 'rgba(96, 165, 250, 0.18)' : 'rgba(15, 98, 254, 0.12)',
      '--color-accent-soft': theme.isDark ? 'rgba(45, 212, 191, 0.16)' : 'rgba(15, 118, 110, 0.12)',
      '--color-success': theme.isDark ? '#86efac' : '#15803d',
      '--color-warning': theme.isDark ? '#fbbf24' : '#b45309',
      '--color-danger': theme.isDark ? '#fca5a5' : '#b91c1c',
      '--color-toolbar': theme.isDark ? 'rgba(21, 27, 35, 0.96)' : 'rgba(255, 255, 255, 0.96)'
    };
    Object.entries(defaults).forEach(([property, value]) => {
      root.style.setProperty(property, theme.customProperties[property] ?? value);
    });

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
