import { useState, useEffect, useRef, useCallback } from 'react';

export interface NewsItem {
  timestamp: string;
  title: string;
  description: string;
  link: string;
  identifier: string;
}

export interface WebSocketMessage {
  type: string;
  items?: NewsItem[];
  count?: number;
  polling_active?: boolean;
  url?: string;
  timestamp: string;
  message?: string;
}

export interface WebSocketState {
  items: NewsItem[];
  isConnected: boolean;
  isPollingActive: boolean;
  error: string | null;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export const useWebSocket = (url: string) => {
  const [state, setState] = useState<WebSocketState>({
    items: [],
    isConnected: false,
    isPollingActive: false,
    error: null,
    connectionStatus: 'disconnected'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({ ...prev, connectionStatus: 'connecting', error: null }));

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({ 
          ...prev, 
          isConnected: true, 
          connectionStatus: 'connected',
          error: null 
        }));
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('Received message:', message);

          setState(prev => {
            const newState = { ...prev };

            switch (message.type) {
              case 'initial_data':
                newState.items = message.items || [];
                newState.isPollingActive = message.polling_active || false;
                break;
              
              case 'new_items':
                // Add new items to the beginning of the list
                if (message.items) {
                  newState.items = [...message.items, ...prev.items];
                }
                break;
              
              case 'status_update':
                newState.isPollingActive = message.polling_active || false;
                break;
              
              case 'error':
                newState.error = message.message || 'Unknown error occurred';
                break;
              
              case 'pong':
                // Handle pong response
                console.log('Received pong');
                break;
              
              default:
                console.log('Unknown message type:', message.type);
            }

            return newState;
          });
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setState(prev => ({ 
            ...prev, 
            error: 'Error parsing server message' 
          }));
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ 
          ...prev, 
          connectionStatus: 'error',
          error: 'WebSocket connection error' 
        }));
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setState(prev => ({ 
          ...prev, 
          isConnected: false, 
          connectionStatus: 'disconnected' 
        }));

        // Attempt to reconnect if it wasn't a manual close
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setState(prev => ({ 
            ...prev, 
            error: 'Maximum reconnection attempts reached' 
          }));
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setState(prev => ({ 
        ...prev, 
        connectionStatus: 'error',
        error: 'Failed to create WebSocket connection' 
      }));
    }
  }, [url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    setState(prev => ({ 
      ...prev, 
      isConnected: false, 
      connectionStatus: 'disconnected' 
    }));
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const ping = useCallback(() => {
    sendMessage({ type: 'ping' });
  }, [sendMessage]);

  useEffect(() => {
    connect();

    // Setup ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        ping();
      }
    }, 30000); // Ping every 30 seconds

    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, ping]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    ping
  };
}; 