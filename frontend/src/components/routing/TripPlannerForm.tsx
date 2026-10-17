import React from 'react';
import { MapPin, Clock, Truck, Sliders, Navigation, RefreshCw } from 'lucide-react';

interface TripPlannerFormProps {
  origin: string;
  setOrigin: (v: string) => void;
  destination: string;
  setDestination: (v: string) => void;
  departure: string;
  setDeparture: (v: string) => void;
  loadWeight: string;
  setLoadWeight: (v: string) => void;
  spacingMiles: '10' | '25' | '50';
  setSpacingMiles: (v: '10' | '25' | '50') => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

export const TripPlannerForm: React.FC<TripPlannerFormProps> = ({
  origin,
  setOrigin,
  destination,
  setDestination,
  departure,
  setDeparture,
  loadWeight,
  setLoadWeight,
  spacingMiles,
  setSpacingMiles,
  onSubmit,
  isLoading,
}) => {
  return (
    <form className="panel form" onSubmit={onSubmit}>
      <div className="panel-header">
        <div>
          <span className="section-kicker">DISPATCH CONFIGURATION</span>
          <h2>Plan Trip Routes</h2>
        </div>
        <Navigation size={20} className="header-icon" />
      </div>

      <div className="form-group">
        <label htmlFor="input-origin">
          <MapPin size={14} /> ORIGIN CITY / LOCATION
        </label>
        <input
          id="input-origin"
          type="text"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="e.g. New York, NY"
          required
          minLength={2}
          disabled={isLoading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="input-destination">
          <MapPin size={14} /> DESTINATION CITY / LOCATION
        </label>
        <input
          id="input-destination"
          type="text"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          placeholder="e.g. Philadelphia, PA"
          required
          minLength={2}
          disabled={isLoading}
        />
      </div>

      <div className="two-columns">
        <div className="form-group">
          <label htmlFor="input-departure">
            <Clock size={14} /> DEPARTURE TIME
          </label>
          <input
            id="input-departure"
            type="datetime-local"
            value={departure}
            onChange={(e) => setDeparture(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="input-load">
            <Truck size={14} /> CARGO LOAD (LBS)
          </label>
          <input
            id="input-load"
            type="number"
            min="0"
            max="100000"
            step="1000"
            value={loadWeight}
            onChange={(e) => setLoadWeight(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="input-spacing">
          <Sliders size={14} /> CHECKPOINT SPACING INTERVAL
        </label>
        <select
          id="input-spacing"
          value={spacingMiles}
          onChange={(e) => setSpacingMiles(e.target.value as '10' | '25' | '50')}
          disabled={isLoading}
        >
          <option value="10">High precision — Every 10 miles</option>
          <option value="25">Standard transit — Every 25 miles</option>
          <option value="50">Long haul — Every 50 miles</option>
        </select>
      </div>

      <button type="submit" className="primary" disabled={isLoading}>
        {isLoading ? (
          <>
            <RefreshCw className="spin" size={17} />
            Analyzing routes & corridor radar...
          </>
        ) : (
          <>
            <Navigation size={17} />
            Analyze Safest Route Alternatives
          </>
        )}
      </button>
    </form>
  );
};

