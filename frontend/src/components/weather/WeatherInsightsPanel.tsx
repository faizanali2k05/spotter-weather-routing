import React from 'react';
import { Wind, Droplets, Snowflake, AlertTriangle, Clock, ShieldCheck } from 'lucide-react';
import { TripRoute } from '../../types';

interface WeatherInsightsPanelProps {
  route: TripRoute | null;
}

export const WeatherInsightsPanel: React.FC<WeatherInsightsPanelProps> = ({ route }) => {
  const checkpoints = route?.checkpoints || [];

  const peakWind = checkpoints.length > 0
    ? Math.max(...checkpoints.map((c) => c.weather.wind_mph)).toFixed(1)
    : '--';

  const maxRain = checkpoints.length > 0
    ? Math.max(...checkpoints.map((c) => c.weather.rain_inches_hr)).toFixed(2)
    : '--';

  const maxSnow = checkpoints.length > 0
    ? Math.max(...checkpoints.map((c) => c.weather.snow_inches_hr)).toFixed(2)
    : '--';

  const highRiskPointsCount = checkpoints.filter(
    (c) => c.risk === 'High' || c.risk === 'Severe' || c.risk === 'No Travel'
  ).length;

  const arrivalFormatted = route
    ? new Date(route.arrival).toLocaleString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : '--';

  return (
    <div className="panel insights-panel">
      <div className="panel-header">
        <div>
          <span className="section-kicker">WEATHER INTELLIGENCE</span>
          <h2>Transit Conditions</h2>
        </div>
        <ShieldCheck size={20} className="header-icon" />
      </div>

      <div className="insight-grid">
        <div className="metric-box">
          <div className="metric-header">
            <Wind size={16} />
            <small>PEAK WIND</small>
          </div>
          <strong>
            {peakWind} <span>mph</span>
          </strong>
        </div>

        <div className="metric-box">
          <div className="metric-header">
            <Droplets size={16} />
            <small>MAX RAIN</small>
          </div>
          <strong>
            {maxRain} <span>in/hr</span>
          </strong>
        </div>

        <div className="metric-box">
          <div className="metric-header">
            <Snowflake size={16} />
            <small>MAX SNOW</small>
          </div>
          <strong>
            {maxSnow} <span>in/hr</span>
          </strong>
        </div>

        <div className="metric-box">
          <div className="metric-header">
            <AlertTriangle size={16} />
            <small>CRITICAL WAYPOINTS</small>
          </div>
          <strong className={highRiskPointsCount > 0 ? 'text-warning' : ''}>
            {checkpoints.length > 0 ? highRiskPointsCount : '--'} <span>points</span>
          </strong>
        </div>
      </div>

      {route && (
        <div className="arrival-strip">
          <Clock size={15} />
          <span>
            Estimated Arrival: <strong>{arrivalFormatted}</strong> ({route.distance_miles.toFixed(1)} miles)
          </span>
        </div>
      )}
    </div>
  );
};
