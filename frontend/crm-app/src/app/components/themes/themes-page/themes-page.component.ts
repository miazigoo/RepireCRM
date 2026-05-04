import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  InterfaceStyle,
  Theme,
  ThemeService
} from '../../../services/theme.service';

type ThemeModeFilter = 'all' | 'light' | 'dark';

@Component({
  selector: 'app-themes-page',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatTooltipModule
  ],
  templateUrl: './themes-page.component.html',
  styleUrl: './themes-page.component.css'
})
export class ThemesPageComponent implements OnInit {
  themes: Theme[] = [];
  styles: InterfaceStyle[] = [];
  currentTheme!: Theme;
  currentStyle!: InterfaceStyle;
  modeFilter: ThemeModeFilter = 'all';

  constructor(private themeService: ThemeService) {}

  ngOnInit(): void {
    this.themes = this.themeService.getAvailableThemes();
    this.styles = this.themeService.getAvailableStyles();
    this.currentTheme = this.themeService.getCurrentTheme();
    this.currentStyle = this.themeService.getCurrentStyle();

    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });

    this.themeService.currentStyle$.subscribe(style => {
      this.currentStyle = style;
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

  selectStyle(styleId: string): void {
    this.themeService.setStyle(styleId);
  }

  trackById(_: number, item: Theme | InterfaceStyle): string {
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

  getThemePalette(theme: Theme): string[] {
    return [
      theme.colors.primary,
      theme.colors.accent,
      theme.colors.secondary,
      theme.colors.warn,
      theme.colors.background
    ];
  }
}
