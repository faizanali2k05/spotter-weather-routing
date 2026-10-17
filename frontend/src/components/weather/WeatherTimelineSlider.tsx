import React from 'react';
import { CloudSun, Layers, Eye, EyeOff } from 'lucide-react';
import { TripPlan } from '../../types';

interface WeatherTimelineSliderProps {
  plan: TripPlan | null;
  forecastHour: number;
  setForecastHour: (h: number) => void;
  showHeatmap: boolean;
  setShowHeatmap: (show: boolean) => void;
}

export const WeatherTimelineSlider: React.FC<WeatherTimelineSliderProps> = ({
  plan,
  forecastHour,
  setForecastHour,
  showHeatmap,
  setShowHeatmap,
}) => {
  const departureDate = plan ? new Date(plan.departure) : new Date();
  const timelineDate = new Date(departureDate.getTime() + forecastHour * 3600 * 1000);

  const formattedDate = timelineDate.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  return (
    <div className="panel forecast-panel">
      <div className="panel-header">
        <div>
          <span className="section-kicker">SPATIAL FORECAST RADAR</span>
          <h2>48-Hour Corridor Timeline</h2>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className={`toggle-btn ${showHeatmap ? 'active' : ''}`}
            onClick={() => setShowHeatmap(!showHeatmap)}
            title="Toggle spatial weather heatmap overlay"
          >
            {showHeatmap ? <Eye size={14} /> : <EyeOff size={14} />}
            <span>Heatmap Overlay</span>
          </button>
          <CloudSun size={20} className="header-icon" />
        </div>
      </div>

      <div className="forecast-display">
        <div className="forecast-val">
          <strong>+{forecastHour}h</strong>
          <span className="forecast-time-label">Valid: {formattedDate}</span>
        </div>
      </div>

      <div className="slider-wrapper">
        <input
          id="forecast-range"
          aria-label="Forecast horizon timeline in hours"
          className="range-slider"
          type="range"
          min="0"
          max="48"
          step="3"
          value={forecastHour}
          onChange={(e) => setForecastHour(Number(e.target.value))}
        />
        <div className="ticks">
          <span>DEPARTURE (+0H)</span>
          <span>+12H</span>
          <span>+24H</span>
          <span>+36H</span>
          <span>+48H</span>
        </div>
      </div>

      <div className="timeline-explanation">
        <Layers size={14} />
        <span>
          Dynamic heatmap reflects regional weather forecast at <strong>+{forecastHour}h</strong> across the entire travel corridor.
        </span>
      </div>
    </div>
  );
};
