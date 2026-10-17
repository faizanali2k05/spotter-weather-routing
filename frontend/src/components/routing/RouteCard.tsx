import React from 'react';
import { Route, Clock, ShieldCheck, AlertTriangle } from 'lucide-react';
import { TripRoute, RiskLevel } from '../../types';
import { RISK_COLORS } from '../../utils/constants';

interface RouteCardProps {
  route: TripRoute;
  isSelected: boolean;
  onSelect: () => void;
}

export const RouteCard: React.FC<RouteCardProps> = ({ route, isSelected, onSelect }) => {
  const miles = route.summary.miles_by_risk;
  const dist = Math.max(1, route.distance_miles);

  const hours = Math.floor(route.duration_minutes / 60);
  const mins = route.duration_minutes % 60;

  const hasNoTravel = route.summary.no_travel;

  return (
    <button
      type="button"
      className={`route-item ${isSelected ? 'selected' : ''} ${hasNoTravel ? 'has-no-travel' : ''}`}
      onClick={onSelect}
      aria-pressed={isSelected}
    >
      <div className="route-top">
        <div className="route-header-left">
          <span className="route-name">Route {route.id}</span>
          {route.recommended && (
            <span className="safe-badge">
              <ShieldCheck size={12} /> RECOMMENDED
            </span>
          )}
          {hasNoTravel && (
            <span className="danger-badge">
              <AlertTriangle size={12} /> NO TRAVEL
            </span>
          )}
        </div>
        <span className="route-arrow">↗</span>
      </div>

      <div className="route-stats">
        <span>
          <Route size={13} /> {route.distance_miles.toFixed(1)} mi
        </span>
        <span>
          <Clock size={13} /> {hours > 0 ? `${hours}h ` : ''}{mins}m
        </span>
        <span className="severity-pill" style={{ color: RISK_COLORS[route.summary.worst_severity] }}>
          Worst: {route.summary.worst_severity}
        </span>
      </div>

      {/* Exposure Breakdown Meter */}
      <div className="meter" title="Mileage exposed to weather severity">
        {(['Low', 'Moderate', 'High', 'Severe', 'No Travel'] as RiskLevel[]).map((level) => {
          const m = miles[level] || 0;
          const pct = (m / dist) * 100;
          if (pct <= 0) return null;
          return (
            <span
              key={level}
              style={{
                width: `${pct}%`,
                backgroundColor: RISK_COLORS[level],
              }}
              title={`${level}: ${m.toFixed(1)} miles (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>

      <div className="route-foot">
        <span>
          Severe: {miles['Severe']?.toFixed(0) || 0} mi · High: {miles['High']?.toFixed(0) || 0} mi
        </span>
        <span className="route-score">
          {hasNoTravel ? 'UNSAFE' : `RISK INDEX ${route.summary.average_risk.toFixed(2)}`}
        </span>
      </div>

      {/* Rationale explanation */}
      {route.recommendation_reason && (
        <div className="route-reason">
          <small>{route.recommendation_reason}</small>
        </div>
      )}
    </button>
  );
};

