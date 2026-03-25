/**
 * Daedalus Mobile — Centralized Design Tokens
 *
 * Mirrors the cockpit's dark aesthetic with mobile-native adjustments.
 * All components should import from here — never hard-code colors.
 */

export const colors = {
  bg: '#05060A',
  surface: '#0B0D16',
  surfaceElevated: '#101424',
  border: '#262A3F',
  borderSubtle: '#1A1E30',

  text: '#E6EDF3',
  textSecondary: '#C3C7E0',
  textMuted: '#8B949E',
  textFaint: '#6C7299',

  accent: '#58A6FF',
  accentDim: 'rgba(88, 166, 255, 0.12)',
  accentBorder: 'rgba(88, 166, 255, 0.2)',

  green: '#3FB950',
  greenDim: 'rgba(63, 185, 80, 0.15)',
  red: '#F85149',
  redDim: 'rgba(248, 81, 73, 0.15)',
  yellow: '#D29922',
  yellowDim: 'rgba(210, 153, 34, 0.15)',
  purple: '#8B5CF6',
  purpleDim: 'rgba(139, 92, 246, 0.12)',

  buttonBg: '#1C2140',
  buttonBgActive: '#252B52',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  pill: 999,
} as const;

export const fonts = {
  body: 14,
  small: 12,
  caption: 11,
  micro: 10,
  title: 20,
  subtitle: 16,
  header: 24,
} as const;
