import React from 'react';
import { RiskLevel } from '../../types';
import { RISK_COLORS } from '../../utils/constants';

const RISK_LEVELS: RiskLevel[] = ['Low', 'Moderate', 'High', 'Severe', 'No Travel'];

export const HazardLegend: React.FC = () => {
  return (
    <div className="hazard-legend" aria-label="Risk Severity Legend">
      {RISK_LEVELS.map((level) => (
        <span key={level} className="legend-item">
          <i style={{ backgroundColor: RISK_COLORS[level] }} />
          <span>{level}</span>
        </span>
      ))}
    </div>
  );
};
