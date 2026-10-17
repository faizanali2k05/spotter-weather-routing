import { useState, useCallback } from 'react';
import { TripPlan, PlanRequest } from '../types';
import { requestTripPlan, ApiError } from '../services/api';

function getInitialDeparture(): string {
  const dt = new Date(Date.now() + 3600000); // 1 hour in the future
  return new Date(dt.getTime() - dt.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function useRoutePlanner() {
  const [origin, setOrigin] = useState('New York, NY');
  const [destination, setDestination] = useState('Philadelphia, PA');
  const [departure, setDeparture] = useState(getInitialDeparture);
  const [loadWeight, setLoadWeight] = useState('35000');
  const [spacingMiles, setSpacingMiles] = useState<'10' | '25' | '50'>('25');

  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [forecastHour, setForecastHour] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showCheckpoints, setShowCheckpoints] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const calculateRoutes = useCallback(async (customPayload?: Partial<PlanRequest>) => {
    setIsLoading(true);
    setErrorMessage(null);
    setErrorCode(null);

    const departureDate = new Date(customPayload?.departure || departure);
    const payload: PlanRequest = {
      origin: customPayload?.origin ?? origin,
      destination: customPayload?.destination ?? destination,
      departure: departureDate.toISOString(),
      load_lbs: Number(customPayload?.load_lbs ?? loadWeight),
      spacing_miles: Number(customPayload?.spacing_miles ?? spacingMiles),
    };

    try {
      const data = await requestTripPlan(payload);
      setPlan(data);
      setSelectedRouteIndex(0);
      setForecastHour(0);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        setErrorCode(err.code);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred while analyzing routes.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [origin, destination, departure, loadWeight, spacingMiles]);

  const activeRoute = plan?.routes[selectedRouteIndex] ?? null;

  return {
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
    plan,
    selectedRouteIndex,
    setSelectedRouteIndex,
    activeRoute,
    forecastHour,
    setForecastHour,
    showHeatmap,
    setShowHeatmap,
    showCheckpoints,
    setShowCheckpoints,
    isLoading,
    errorMessage,
    errorCode,
    calculateRoutes,
  };
}

