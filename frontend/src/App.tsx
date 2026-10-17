import React from 'react';
import { Sidebar } from './components/common/Sidebar';
import { Header } from './components/common/Header';
import { ErrorBanner } from './components/common/ErrorBanner';
import { TripPlannerForm } from './components/routing/TripPlannerForm';
import { RouteComparisonList } from './components/routing/RouteComparisonList';
import { MapView } from './components/map/MapView';
import { WeatherTimelineSlider } from './components/weather/WeatherTimelineSlider';
import { WeatherInsightsPanel } from './components/weather/WeatherInsightsPanel';
import { useRoutePlanner } from './hooks/useRoutePlanner';
import { AlertTriangle } from 'lucide-react';

export const App: React.FC = () => {
  const {
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
    isLoading,
    errorMessage,
    errorCode,
    calculateRoutes,
  } = useRoutePlanner();

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    calculateRoutes();
  };

  return (
    <div className="app">
      <Sidebar />

      <main className="main">
        <Header />

        {errorMessage && (
          <ErrorBanner
            message={errorMessage}
            code={errorCode}
            onRetry={() => calculateRoutes()}
          />
        )}

        <div className="workspace">
          {/* Left Column: Form + Route Alternatives List */}
          <section className="left">
            <TripPlannerForm
              origin={origin}
              setOrigin={setOrigin}
              destination={destination}
              setDestination={setDestination}
              departure={departure}
              setDeparture={setDeparture}
              loadWeight={loadWeight}
              setLoadWeight={setLoadWeight}
              spacingMiles={spacingMiles}
              setSpacingMiles={setSpacingMiles}
              onSubmit={handleFormSubmit}
              isLoading={isLoading}
            />

            <RouteComparisonList
              plan={plan}
              selectedRouteIndex={selectedRouteIndex}
              onSelectRoute={setSelectedRouteIndex}
            />
          </section>

          {/* Right Column: Interactive Map + Timeline Slider + Weather Insights */}
          <section className="right">
            <MapView
              plan={plan}
              selectedRouteIndex={selectedRouteIndex}
              forecastHour={forecastHour}
              showHeatmap={showHeatmap}
              showCheckpoints={showCheckpoints}
            />

            <div className="bottom-grid">
              <WeatherTimelineSlider
                plan={plan}
                forecastHour={forecastHour}
                setForecastHour={setForecastHour}
                showHeatmap={showHeatmap}
                setShowHeatmap={setShowHeatmap}
              />

              <WeatherInsightsPanel route={activeRoute} />
            </div>

            <footer className="disclaimer" role="contentinfo">
              <AlertTriangle size={15} />
              <span>
                {plan?.warning ||
                  'Advisory planning tool only. Route geometries use OSRM general driving directions and are not validated for commercial truck restrictions. Always check official DOT road closures and National Weather Service alerts prior to departure.'}
              </span>
            </footer>
          </section>
        </div>
      </main>
    </div>
  );
};

