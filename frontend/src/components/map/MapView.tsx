import React, { useEffect, useRef } from 'react';
import maplibregl, { Map as MLMap, GeoJSONSource, LngLatBounds } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { TripPlan, Checkpoint } from '../../types';
import { RISK_COLORS, MAP_STYLES } from '../../utils/constants';
import { HazardLegend } from '../weather/HazardLegend';
import { Navigation, Layers } from 'lucide-react';

interface MapViewProps {
  plan: TripPlan | null;
  selectedRouteIndex: number;
  forecastHour: number;
  showHeatmap: boolean;
  showCheckpoints: boolean;
}

export const MapView: React.FC<MapViewProps> = ({
  plan,
  selectedRouteIndex,
  forecastHour,
  showHeatmap,
  showCheckpoints,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);

  // Initialize MapLibre GL map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLES.dark,
      center: [-74.8, 40.3], // Default center around mid-Atlantic corridor
      zoom: 6.5,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Route Polylines and Checkpoints
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !plan || plan.routes.length === 0) return;

    const renderLayers = () => {
      const activeRoute = plan.routes[selectedRouteIndex] || plan.routes[0];

      // 1. Route polylines GeoJSON
      const routesGeoJSON: GeoJSON.FeatureCollection<GeoJSON.LineString> = {
        type: 'FeatureCollection',
        features: plan.routes.map((route, idx) => ({
          type: 'Feature',
          properties: {
            routeIndex: idx,
            isSelected: idx === selectedRouteIndex,
            color: idx === selectedRouteIndex ? '#32cfc1' : '#556f80',
          },
          geometry: {
            type: 'LineString',
            coordinates: route.geometry,
          },
        })),
      };

      const routesSource = map.getSource('routes-source') as GeoJSONSource | undefined;
      if (routesSource) {
        routesSource.setData(routesGeoJSON);
      } else {
        map.addSource('routes-source', {
          type: 'geojson',
          data: routesGeoJSON,
        });
      }

      if (!map.getLayer('route-lines')) {
        map.addLayer({
          id: 'route-lines',
          type: 'line',
          source: 'routes-source',
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': ['get', 'color'],
            'line-width': ['case', ['get', 'isSelected'], 6.5, 3.5],
            'line-opacity': ['case', ['get', 'isSelected'], 0.95, 0.65],
          },
        });
      } else {
        map.setPaintProperty('route-lines', 'line-width', ['case', ['get', 'isSelected'], 6.5, 3.5]);
        map.setPaintProperty('route-lines', 'line-opacity', ['case', ['get', 'isSelected'], 0.95, 0.65]);
      }

      // 2. Checkpoints GeoJSON for active route
      const checkpointsGeoJSON: GeoJSON.FeatureCollection<GeoJSON.Point> = {
        type: 'FeatureCollection',
        features: activeRoute.checkpoints.map((pt) => ({
          type: 'Feature',
          properties: {
            mile: pt.mile,
            eta: pt.eta,
            risk: pt.risk,
            color: RISK_COLORS[pt.risk],
            wind: pt.weather.wind_mph,
            rain: pt.weather.rain_inches_hr,
            snow: pt.weather.snow_inches_hr,
            factors: pt.factors.join(', '),
          },
          geometry: {
            type: 'Point',
            coordinates: [pt.lon, pt.lat],
          },
        })),
      };

      const checkpointSource = map.getSource('checkpoints-source') as GeoJSONSource | undefined;
      if (checkpointSource) {
        checkpointSource.setData(checkpointsGeoJSON);
      } else {
        map.addSource('checkpoints-source', {
          type: 'geojson',
          data: checkpointsGeoJSON,
        });
      }

      // Halo layer
      if (!map.getLayer('checkpoint-halo')) {
        map.addLayer({
          id: 'checkpoint-halo',
          type: 'circle',
          source: 'checkpoints-source',
          paint: {
            'circle-color': ['get', 'color'],
            'circle-radius': 16,
            'circle-opacity': 0.2,
            'circle-blur': 0.6,
          },
        });
      }

      // Point core layer
      if (!map.getLayer('checkpoint-points')) {
        map.addLayer({
          id: 'checkpoint-points',
          type: 'circle',
          source: 'checkpoints-source',
          paint: {
            'circle-color': ['get', 'color'],
            'circle-radius': 6.5,
            'circle-stroke-color': '#061922',
            'circle-stroke-width': 2,
          },
        });
      }

      map.setLayoutProperty('checkpoint-halo', 'visibility', showCheckpoints ? 'visible' : 'none');
      map.setLayoutProperty('checkpoint-points', 'visibility', showCheckpoints ? 'visible' : 'none');

      // Checkpoint click popup
      map.off('click', 'checkpoint-points', handleCheckpointClick);
      map.on('click', 'checkpoint-points', handleCheckpointClick);

      function handleCheckpointClick(e: maplibregl.MapLayerMouseEvent) {
        const feature = e.features?.[0];
        if (!feature || !map) return;
        const p = feature.properties as any;
        const coords = (feature.geometry as GeoJSON.Point).coordinates as [number, number];

        const localEta = new Date(p.eta).toLocaleString(undefined, {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        });

        new maplibregl.Popup({ closeButton: true, offset: 12 })
          .setLngLat(coords)
          .setHTML(`
            <div class="map-popup">
              <div class="popup-header" style="border-left: 4px solid ${p.color}">
                <strong>${p.risk} Risk Waypoint</strong>
                <span>Mile ${Number(p.mile).toFixed(1)}</span>
              </div>
              <div class="popup-body">
                <p><strong>ETA:</strong> ${localEta}</p>
                <div class="popup-weather-grid">
                  <div><span>Wind:</span> <strong>${p.wind} mph</strong></div>
                  <div><span>Rain:</span> <strong>${p.rain} in/hr</strong></div>
                  <div><span>Snow:</span> <strong>${p.snow} in/hr</strong></div>
                </div>
                ${p.factors ? `<p class="popup-factors"><em>${p.factors}</em></p>` : ''}
              </div>
            </div>
          `)
          .addTo(map);
      }

      // 3. Markers for Origin and Destination
      if (originMarkerRef.current) originMarkerRef.current.remove();
      if (destMarkerRef.current) destMarkerRef.current.remove();

      const origEl = document.createElement('div');
      origEl.className = 'custom-map-marker origin-marker';
      origEl.innerHTML = '<span>A</span>';
      originMarkerRef.current = new maplibregl.Marker({ element: origEl })
        .setLngLat([plan.origin.lon, plan.origin.lat])
        .setPopup(new maplibregl.Popup().setText(`Origin: ${plan.origin.name}`))
        .addTo(map);

      const destEl = document.createElement('div');
      destEl.className = 'custom-map-marker dest-marker';
      destEl.innerHTML = '<span>B</span>';
      destMarkerRef.current = new maplibregl.Marker({ element: destEl })
        .setLngLat([plan.destination.lon, plan.destination.lat])
        .setPopup(new maplibregl.Popup().setText(`Destination: ${plan.destination.name}`))
        .addTo(map);

      // Fit bounds to the active route geometry
      const bounds = new LngLatBounds();
      activeRoute.geometry.forEach((coord) => bounds.extend(coord));
      map.fitBounds(bounds, { padding: 60, maxZoom: 11, duration: 800 });
    };

    if (map.isStyleLoaded()) {
      renderLayers();
    } else {
      map.once('load', renderLayers);
    }
  }, [plan, selectedRouteIndex, showCheckpoints]);

  // Phase 7: Dynamic Spatial Corridor Weather Heatmap Layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !plan?.corridor_heatmap) return;

    const renderHeatmap = () => {
      const frames = plan.corridor_heatmap?.frames || [];
      if (frames.length === 0) return;

      // Find closest frame to the current forecast hour
      let bestFrame = frames[0];
      let minDiff = 999;
      for (const f of frames) {
        const diff = Math.abs(f.forecast_hour - forecastHour);
        if (diff < minDiff) {
          minDiff = diff;
          bestFrame = f;
        }
      }

      const heatmapGeoJSON: GeoJSON.FeatureCollection<GeoJSON.Point> = {
        type: 'FeatureCollection',
        features: bestFrame.points.map((pt) => ({
          type: 'Feature',
          properties: {
            weight: pt.weight,
            risk: pt.risk,
            wind: pt.wind_mph,
            rain: pt.rain_inches_hr,
            snow: pt.snow_inches_hr,
            dominant: pt.dominant_factor,
          },
          geometry: {
            type: 'Point',
            coordinates: [pt.lon, pt.lat],
          },
        })),
      };

      const heatmapSource = map.getSource('corridor-heatmap-source') as GeoJSONSource | undefined;
      if (heatmapSource) {
        heatmapSource.setData(heatmapGeoJSON);
      } else {
        map.addSource('corridor-heatmap-source', {
          type: 'geojson',
          data: heatmapGeoJSON,
        });
      }

      if (!map.getLayer('corridor-heatmap-layer')) {
        map.addLayer(
          {
            id: 'corridor-heatmap-layer',
            type: 'heatmap',
            source: 'corridor-heatmap-source',
            maxzoom: 12,
            paint: {
              // Weight based on computed risk score (0.1 to 1.0)
              'heatmap-weight': ['get', 'weight'],
              // Intensity multiplier based on zoom
              'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 0.8,
                7, 1.8,
                11, 3.0,
              ],
              // Color ramp transitioning through Low, Moderate, High, Severe, No Travel
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(0, 0, 0, 0)',
                0.2, 'rgba(38, 189, 148, 0.45)',   // Low (Green)
                0.45, 'rgba(241, 199, 91, 0.65)',  // Moderate (Amber)
                0.68, 'rgba(245, 158, 75, 0.78)',  // High (Orange)
                0.85, 'rgba(240, 98, 110, 0.88)',  // Severe (Red)
                1.0, 'rgba(189, 93, 242, 0.95)',   // No Travel (Purple)
              ],
              // Radius of influence in pixels
              'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 25,
                6, 50,
                10, 85,
              ],
              // Overall opacity
              'heatmap-opacity': 0.65,
            },
          },
          'route-lines' // Render underneath the route line
        );
      }

      map.setLayoutProperty('corridor-heatmap-layer', 'visibility', showHeatmap ? 'visible' : 'none');
    };

    if (map.isStyleLoaded()) {
      renderHeatmap();
    } else {
      map.once('load', renderHeatmap);
    }
  }, [plan, forecastHour, showHeatmap]);

  return (
    <div className="map-card">
      <div className="map" ref={mapContainerRef} />

      <div className="map-overlay">
        <div className="map-title-card">
          <span className="map-kicker">INTERACTIVE ROUTE MAP</span>
          <strong>{plan ? `${plan.origin.name.split(',')[0]} → ${plan.destination.name.split(',')[0]}` : 'Corridor Overview'}</strong>
        </div>

        <HazardLegend />
      </div>

      {!plan && (
        <div className="map-tip">
          <Navigation size={18} />
          <span>Enter origin and destination to visualize routes, waypoints, and weather risk heatmap.</span>
        </div>
      )}

      {showHeatmap && plan?.corridor_heatmap && (
        <div className="heatmap-indicator-pill">
          <Layers size={13} />
          <span>Spatial Weather Radar: +{forecastHour}h Horizon</span>
        </div>
      )}
    </div>
  );
};
