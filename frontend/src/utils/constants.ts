import { RiskLevel } from '../types';

export const RISK_COLORS: Record<RiskLevel, string> = {
  'Low': '#26bd94',       // Emerald green
  'Moderate': '#f1c75b',  // Amber yellow
  'High': '#f59e4b',      // Warning orange
  'Severe': '#f0626e',    // Coral red
  'No Travel': '#bd5df2', // Vivid purple/magenta
};

export const RISK_BG_COLORS: Record<RiskLevel, string> = {
  'Low': 'rgba(38, 189, 148, 0.15)',
  'Moderate': 'rgba(241, 199, 91, 0.15)',
  'High': 'rgba(245, 158, 75, 0.18)',
  'Severe': 'rgba(240, 98, 110, 0.20)',
  'No Travel': 'rgba(189, 93, 242, 0.25)',
};

export const MAP_STYLES = {
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  voyager: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
};

