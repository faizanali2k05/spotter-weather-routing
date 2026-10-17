import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  code?: string | null;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, code, onRetry }) => {
  return (
    <div className="error-banner" role="alert">
      <div className="error-banner-content">
        <AlertTriangle size={18} className="error-icon" />
        <div>
          <strong>Routing Error {code ? `[${code}]` : ''}</strong>
          <p>{message}</p>
        </div>
      </div>
      {onRetry && (
        <button type="button" className="retry-btn" onClick={onRetry}>
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  );
};
