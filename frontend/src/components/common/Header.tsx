import React from 'react';
import { CloudSun, Radio } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="topbar">
      <div>
        <span className="crumb">FLEET OPERATIONS / DISPATCH ADVISORY</span>
        <h1>
          Weather-Aware Truck Routing
          <span className="title-icon">
            <CloudSun size={26} />
          </span>
        </h1>
        <p>Proactive route comparison, load-dependent wind thresholds, and spatial corridor weather radar.</p>
      </div>

      <div className="live">
        <span className="live-dot" />
        <Radio size={13} style={{ marginRight: 6 }} />
        LIVE FORECAST DATA
      </div>
    </header>
  );
};
