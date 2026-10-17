import React from 'react';
import { Route, AlertTriangle } from 'lucide-react';
import { TripPlan } from '../../types';
import { RouteCard } from './RouteCard';

interface RouteComparisonListProps {
  plan: TripPlan | null;
  selectedRouteIndex: number;
  onSelectRoute: (index: number) => void;
}

export const RouteComparisonList: React.FC<RouteComparisonListProps> = ({
  plan,
  selectedRouteIndex,
  onSelectRoute,
}) => {
  return (
    <div className="panel routes-panel">
      <div className="panel-header">
        <div>
          <span className="section-kicker">ROUTE COMPARISON</span>
          <h2>Evaluated Alternatives</h2>
        </div>
        <span className="count-pill">
          {plan ? `${plan.routes.length} OPTION${plan.routes.length === 1 ? '' : 'S'}` : '0 OPTIONS'}
        </span>
      </div>

      {!plan ? (
        <div className="empty-state">
          <Route size={38} className="empty-icon" />
          <h3>Awaiting Journey Details</h3>
          <p>Configure origin, destination, cargo weight, and departure time to compare road weather conditions.</p>
        </div>
      ) : (
        <>
          {!plan.has_safe_route && (
            <div className="danger-notice" role="alert">
              <AlertTriangle size={18} />
              <div>
                <strong>NO SAFE ROUTE AVAILABLE</strong>
                <p>All evaluated alternatives encounter severe No Travel hazards. Dispatch should be delayed.</p>
              </div>
            </div>
          )}

          <div className="routes-list">
            {plan.routes.map((route, idx) => (
              <RouteCard
                key={route.id}
                route={route}
                isSelected={selectedRouteIndex === idx}
                onSelect={() => onSelectRoute(idx)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

