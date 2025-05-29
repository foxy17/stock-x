import { WebSocketState } from '../hooks/useWebSocket';
import './StatusBar.css';

interface StatusBarProps {
  status: WebSocketState;
  onReconnect?: () => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({ status, onReconnect }) => {
  const getStatusColor = () => {
    switch (status.connectionStatus) {
      case 'connected':
        return '#4caf50';
      case 'connecting':
        return '#ff9800';
      case 'disconnected':
        return '#757575';
      case 'error':
        return '#f44336';
      default:
        return '#757575';
    }
  };

  const getStatusText = () => {
    switch (status.connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  const getPollingText = () => {
    if (!status.isConnected) return '';
    return status.isPollingActive ? 'Polling Active' : 'Polling Inactive';
  };

  return (
    <div className="status-bar">
      <div className="status-bar__section">
        <div 
          className="status-indicator"
          style={{ backgroundColor: getStatusColor() }}
        />
        <span className="status-text">{getStatusText()}</span>
      </div>

      {status.isConnected && (
        <div className="status-bar__section">
          <div 
            className={`polling-indicator ${status.isPollingActive ? 'polling-indicator--active' : ''}`}
          />
          <span className="status-text">{getPollingText()}</span>
        </div>
      )}

      <div className="status-bar__section">
        <span className="status-text">
          {status.items.length} item{status.items.length !== 1 ? 's' : ''}
        </span>
      </div>

      {status.error && (
        <div className="status-bar__section status-bar__error">
          <span className="error-text">{status.error}</span>
          {onReconnect && (
            <button 
              className="reconnect-button"
              onClick={onReconnect}
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}; 