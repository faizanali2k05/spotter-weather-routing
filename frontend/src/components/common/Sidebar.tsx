import React from 'react';
import { Route, CloudSun, ShieldCheck, Truck } from 'lucide-react';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brandmark">
          <span />
          <span />
          <span />
        </div>
        <span>spotter<span className="branddot">.</span></span>
        <small>FLEET ROUTING</small>
      </div>

      <div className="aside-label">NAVIGATION CONSOLE</div>

      <nav>
        <button type="button" className="nav active">
          <Route size={17} />
          <span>Weather Routing</span>
        </button>
        <button type="button" className="nav muted">
          <CloudSun size={17} />
          <span>Corridor Radar</span>
        </button>
        <button type="button" className="nav muted">
          <Truck size={17} />
          <span>Fleet Safety</span>
        </button>
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-hint">
          <ShieldCheck size={18} />
          <strong>Weather-First Dispatch</strong>
          <p>Real-time road risk analysis powered by Open-Meteo & OSRM.</p>
        </div>
        <span className="version">Spotter Logistics v2.0</span>
      </div>
    </aside>
  );
};

