import type { WebSocketState } from '../hooks/useWebSocket';
import './StatusBar.css';

interface StatusBarProps {
  status: WebSocketState;
  onReconnect?: () => void;
}

// API functions to control polling
const startPolling = async (url: string = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml") => {
  try {
    const response = await fetch('http://localhost:5127/start-polling', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('Polling started:', result);
    return result;
  } catch (error) {
    console.error('Error starting polling:', error);
    throw error;
  }
};

const stopPolling = async () => {
  try {
    const response = await fetch('http://localhost:5127/stop-polling', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('Polling stopped:', result);
    return result;
  } catch (error) {
    console.error('Error stopping polling:', error);
    throw error;
  }
};

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

  const handleStartPolling = async () => {
    if (!status.isConnected) {
      console.warn('Cannot start polling: not connected to server');
      return;
    }
    
    try {
      await startPolling();
    } catch (error) {
      console.error('Failed to start polling:', error);
    }
  };

  const handleStopPolling = async () => {
    if (!status.isConnected) {
      console.warn('Cannot stop polling: not connected to server');
      return;
    }
    
    try {
      await stopPolling();
    } catch (error) {
      console.error('Failed to stop polling:', error);
    }
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

      {status.isConnected && (
        <div className="status-bar__section">
          <div className="polling-controls">
            {!status.isPollingActive ? (
              <button 
                className="polling-button polling-button--start"
                onClick={handleStartPolling}
                title="Start polling for new announcements"
              >
                ▶ Start
              </button>
            ) : (
              <button 
                className="polling-button polling-button--stop"
                onClick={handleStopPolling}
                title="Stop polling for new announcements"
              >
                ⏸ Stop
              </button>
            )}
          </div>
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