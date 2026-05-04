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

export interface InterfaceStyle {
  id: string;
  name: string;
  displayName: string;
  description: string;
  icon: string;
  customProperties: Record<string, string>;
}

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_STORAGE_KEY = 'selectedTheme';
  private readonly STYLE_STORAGE_KEY = 'selectedInterfaceStyle';
  private currentThemeSubject!: BehaviorSubject<Theme>;
  private currentStyleSubject!: BehaviorSubject<InterfaceStyle>;

  public currentTheme$!: Observable<Theme>;
  public currentStyle$!: Observable<InterfaceStyle>;

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
      id: 'nord-light',
      name: 'nord-light',
      displayName: 'Северное утро',
      description: 'Чистая светлая тема с холодным воздухом и зеленым акцентом',
      isDark: false,
      colors: {
        primary: '#0e7490',
        secondary: '#475569',
        accent: '#16a34a',
        warn: '#dc2626',
        background: '#f1f7f8',
        surface: '#ffffff',
        text: {
          primary: '#102027',
          secondary: '#54656d',
          disabled: '#93a4ac',
          hint: '#93a4ac'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 32px rgba(8,47,73,0.08)',
        '--shadow-medium': '0 18px 48px rgba(8,47,73,0.12)',
        '--shadow-heavy': '0 26px 70px rgba(8,47,73,0.18)',
        '--color-border': '#c9dde2',
        '--color-surface-strong': '#e7f0f2',
        '--color-toolbar': 'rgba(255,255,255,0.96)'
      }
    },
    {
      id: 'coral-light',
      name: 'coral-light',
      displayName: 'Коралл',
      description: 'Светлая тема с энергичным кораллом и спокойным индиго',
      isDark: false,
      colors: {
        primary: '#e11d48',
        secondary: '#1e1b4b',
        accent: '#0d9488',
        warn: '#b91c1c',
        background: '#fff5f6',
        surface: '#ffffff',
        text: {
          primary: '#241521',
          secondary: '#65515d',
          disabled: '#a78b98',
          hint: '#a78b98'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 32px rgba(190,18,60,0.09)',
        '--shadow-medium': '0 18px 48px rgba(190,18,60,0.13)',
        '--shadow-heavy': '0 26px 70px rgba(190,18,60,0.18)',
        '--color-border': '#f0cdd3',
        '--color-surface-strong': '#feecef',
        '--color-toolbar': 'rgba(255,255,255,0.96)'
      }
    },
    {
      id: 'sage-light',
      name: 'sage-light',
      displayName: 'Шалфей',
      description: 'Спокойная светлая тема для долгой работы с таблицами',
      isDark: false,
      colors: {
        primary: '#166534',
        secondary: '#475569',
        accent: '#7c3aed',
        warn: '#dc2626',
        background: '#f3f7f1',
        surface: '#ffffff',
        text: {
          primary: '#17251a',
          secondary: '#56645a',
          disabled: '#95a197',
          hint: '#95a197'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 12px 32px rgba(22,101,52,0.08)',
        '--shadow-medium': '0 18px 48px rgba(22,101,52,0.12)',
        '--shadow-heavy': '0 26px 70px rgba(22,101,52,0.18)',
        '--color-border': '#d2dfcf',
        '--color-surface-strong': '#e8f0e5',
        '--color-toolbar': 'rgba(255,255,255,0.96)'
      }
    },
    {
      id: 'mono-light',
      name: 'mono-light',
      displayName: 'Монохром',
      description: 'Нейтральный интерфейс с резкими акцентами и минимумом шума',
      isDark: false,
      colors: {
        primary: '#111827',
        secondary: '#4b5563',
        accent: '#2563eb',
        warn: '#dc2626',
        background: '#f5f6f8',
        surface: '#ffffff',
        text: {
          primary: '#111827',
          secondary: '#4b5563',
          disabled: '#9ca3af',
          hint: '#9ca3af'
        }
      },
      customProperties: {
        '--sidebar-width': '280px',
        '--header-height': '64px',
        '--border-radius': '6px',
        '--shadow-light': '0 10px 26px rgba(17,24,39,0.08)',
        '--shadow-medium': '0 16px 42px rgba(17,24,39,0.12)',
        '--shadow-heavy': '0 24px 64px rgba(17,24,39,0.18)',
        '--color-border': '#d1d5db',
        '--color-surface-strong': '#eceff3',
        '--color-toolbar': 'rgba(255,255,255,0.96)'
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
      id: 'graphite-gold',
      name: 'graphite-gold',
      displayName: 'Графит и золото',
      description: 'Темный графит с теплым акцентом для вечерней смены',
      isDark: true,
      colors: {
        primary: '#f59e0b',
        secondary: '#a7f3d0',
        accent: '#38bdf8',
        warn: '#fb7185',
        background: '#111111',
        surface: '#1a1a1a',
        text: {
          primary: '#f8fafc',
          secondary: '#d4d4d4',
          disabled: '#737373',
          hint: '#a3a3a3'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.30)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.42)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.52)',
        '--color-border': '#313131',
        '--color-surface-strong': '#252525',
        '--color-toolbar': 'rgba(26,26,26,0.96)'
      }
    },
    {
      id: 'forest-dark',
      name: 'forest-dark',
      displayName: 'Темный лес',
      description: 'Глубокая зеленая тема с мягким желтым акцентом',
      isDark: true,
      colors: {
        primary: '#86efac',
        secondary: '#93c5fd',
        accent: '#facc15',
        warn: '#fb7185',
        background: '#07120b',
        surface: '#102018',
        text: {
          primary: '#f0fdf4',
          secondary: '#c2d8ca',
          disabled: '#64746b',
          hint: '#91a99b'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.30)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.40)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.50)',
        '--color-border': '#24422f',
        '--color-surface-strong': '#183323',
        '--color-toolbar': 'rgba(16,32,24,0.96)'
      }
    },
    {
      id: 'midnight-red',
      name: 'midnight-red',
      displayName: 'Полночь',
      description: 'Контрастная темная тема с красным статусным акцентом',
      isDark: true,
      colors: {
        primary: '#f43f5e',
        secondary: '#a5b4fc',
        accent: '#22d3ee',
        warn: '#fb7185',
        background: '#100f18',
        surface: '#1b1927',
        text: {
          primary: '#f8fafc',
          secondary: '#d8d7e5',
          disabled: '#78758d',
          hint: '#aaa6bc'
        }
      },
      customProperties: {
        '--sidebar-width': '292px',
        '--header-height': '64px',
        '--border-radius': '8px',
        '--shadow-light': '0 16px 40px rgba(0,0,0,0.30)',
        '--shadow-medium': '0 22px 58px rgba(0,0,0,0.40)',
        '--shadow-heavy': '0 28px 72px rgba(0,0,0,0.50)',
        '--color-border': '#353246',
        '--color-surface-strong': '#262337',
        '--color-toolbar': 'rgba(27,25,39,0.96)'
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

  private interfaceStyles: InterfaceStyle[] = [
    {
      id: 'balanced',
      name: 'interface-balanced',
      displayName: 'Сбалансированный',
      description: 'Средняя плотность, аккуратные формы, спокойные тени',
      icon: 'dashboard_customize',
      customProperties: {
        '--content-padding': '24px',
        '--section-gap': '20px',
        '--card-radius': '8px',
        '--control-radius': '8px',
        '--button-radius': '12px',
        '--icon-button-radius': '10px',
        '--field-radius': '8px',
        '--table-row-height': '52px'
      }
    },
    {
      id: 'compact',
      name: 'interface-compact',
      displayName: 'Компактный',
      description: 'Больше данных на экране, плотные таблицы и формы',
      icon: 'view_compact',
      customProperties: {
        '--content-padding': '18px',
        '--section-gap': '14px',
        '--card-radius': '6px',
        '--control-radius': '6px',
        '--button-radius': '8px',
        '--icon-button-radius': '8px',
        '--field-radius': '6px',
        '--table-row-height': '44px'
      }
    },
    {
      id: 'comfortable',
      name: 'interface-comfortable',
      displayName: 'Комфортный',
      description: 'Больше воздуха, крупнее зоны клика, мягкая подача',
      icon: 'space_dashboard',
      customProperties: {
        '--content-padding': '32px',
        '--section-gap': '26px',
        '--card-radius': '8px',
        '--control-radius': '8px',
        '--button-radius': '14px',
        '--icon-button-radius': '12px',
        '--field-radius': '8px',
        '--table-row-height': '58px'
      }
    },
    {
      id: 'sharp',
      name: 'interface-sharp',
      displayName: 'Строгий',
      description: 'Плоские поверхности, четкие границы, минимум скруглений',
      icon: 'crop_square',
      customProperties: {
        '--content-padding': '22px',
        '--section-gap': '18px',
        '--card-radius': '4px',
        '--control-radius': '4px',
        '--button-radius': '6px',
        '--icon-button-radius': '6px',
        '--field-radius': '4px',
        '--table-row-height': '50px',
        '--shadow-light': '0 1px 0 rgba(15,23,42,0.10)',
        '--shadow-medium': '0 1px 0 rgba(15,23,42,0.14)'
      }
    },
    {
      id: 'focus',
      name: 'interface-focus',
      displayName: 'Фокус',
      description: 'Выше контраст активных элементов и заметнее фокус',
      icon: 'center_focus_strong',
      customProperties: {
        '--content-padding': '24px',
        '--section-gap': '20px',
        '--card-radius': '8px',
        '--control-radius': '8px',
        '--button-radius': '10px',
        '--icon-button-radius': '10px',
        '--field-radius': '8px',
        '--table-row-height': '52px',
        '--focus-ring-width': '4px'
      }
    }
  ];

  constructor() {
    this.currentThemeSubject = new BehaviorSubject<Theme>(this.getDefaultTheme());
    this.currentStyleSubject = new BehaviorSubject<InterfaceStyle>(
      this.getDefaultStyle()
    );
    this.currentTheme$ = this.currentThemeSubject.asObservable();
    this.currentStyle$ = this.currentStyleSubject.asObservable();
    this.loadSavedTheme();
    this.loadSavedStyle();
    this.applyTheme(this.currentThemeSubject.value);
    this.applyInterfaceStyle(this.currentStyleSubject.value);
  }

  getAvailableThemes(): Theme[] {
    return [...this.themes];
  }

  getAvailableStyles(): InterfaceStyle[] {
    return [...this.interfaceStyles];
  }

  getCurrentTheme(): Theme {
    return this.currentThemeSubject.value;
  }

  getCurrentStyle(): InterfaceStyle {
    return this.currentStyleSubject.value;
  }

  setTheme(themeId: string): void {
    const theme = this.themes.find(t => t.id === themeId);
    if (theme) {
      this.currentThemeSubject.next(theme);
      this.applyTheme(theme);
      this.applyInterfaceStyle(this.currentStyleSubject.value);
      this.saveTheme(theme.id);
    }
  }

  setStyle(styleId: string): void {
    const style = this.interfaceStyles.find(item => item.id === styleId);
    if (style) {
      this.currentStyleSubject.next(style);
      this.applyInterfaceStyle(style);
      this.saveStyle(style.id);
    }
  }

  private getDefaultTheme(): Theme {
    return this.themes[0]; // default-light
  }

  private getDefaultStyle(): InterfaceStyle {
    return this.interfaceStyles[0];
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

  private loadSavedStyle(): void {
    const savedStyleId = localStorage.getItem(this.STYLE_STORAGE_KEY);
    if (savedStyleId) {
      const style = this.interfaceStyles.find(item => item.id === savedStyleId);
      if (style) {
        this.currentStyleSubject.next(style);
      }
    }
  }

  private saveTheme(themeId: string): void {
    localStorage.setItem(this.THEME_STORAGE_KEY, themeId);
  }

  private saveStyle(styleId: string): void {
    localStorage.setItem(this.STYLE_STORAGE_KEY, styleId);
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
      '--color-toolbar': theme.isDark ? 'rgba(21, 27, 35, 0.96)' : 'rgba(255, 255, 255, 0.96)',
      '--focus-ring-width': '3px'
    };
    Object.entries(defaults).forEach(([property, value]) => {
      root.style.setProperty(property, theme.customProperties[property] ?? value);
    });

    // Добавляем/убираем класс для темной темы
    document.body.classList.toggle('dark-theme', theme.isDark);
    document.body.classList.remove(...this.themes.map(t => t.name));
    document.body.classList.add(theme.name);
  }

  private applyInterfaceStyle(style: InterfaceStyle): void {
    const root = document.documentElement;

    Object.entries(style.customProperties).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });

    document.body.classList.remove(...this.interfaceStyles.map(item => item.name));
    document.body.classList.add(style.name);
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
