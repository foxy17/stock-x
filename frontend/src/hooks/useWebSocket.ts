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

// Constants for item limits
const MAX_ITEMS_IN_STATE = 5000;

// Utility function to sort items by timestamp (latest first)
const sortItemsByTimestamp = (items: NewsItem[]): NewsItem[] => {
  const parseTimestamp = (timestamp: string): Date => {
    if (!timestamp) return new Date(0);
    
    try {
      // Try parsing RFC 2822 format (common in RSS feeds)
      const date = new Date(timestamp);
      if (!isNaN(date.getTime())) return date;
    } catch {
      // eslint-disable-line no-empty -- Fall through to next parsing method
    }
    
    try {
      // Try ISO format
      return new Date(timestamp.replace('Z', '+00:00'));
    } catch {
      // eslint-disable-line no-empty -- Fall through to next parsing method
    }
    
    try {
      // Try common formats including the NSE format
      // Simple date parsing for common formats
      const dateStr = timestamp.trim();
      if (dateStr.match(/^\d{4}-\d{2}-\d{2}/)) {
        return new Date(dateStr);
      }
      if (dateStr.match(/^\d{1,2}-\w{3}-\d{4}/)) {
        // Convert format like "29-May-2025 07:00:00" to parseable format
        const converted = dateStr.replace(/(\d{1,2})-(\w{3})-(\d{4})/, '$2 $1, $3');
        return new Date(converted);
      }
    } catch {
      // eslint-disable-line no-empty -- Fall through to default case
    }
    
    // If all parsing fails, return minimum date
    console.warn(`Could not parse timestamp: ${timestamp}`);
    return new Date(0);
  };

  return items.sort((a, b) => {
    const dateA = parseTimestamp(a.timestamp);
    const dateB = parseTimestamp(b.timestamp);
    return dateB.getTime() - dateA.getTime(); // Latest first
  });
};

// Utility function to limit items array to max count, keeping latest items
const limitItemsArray = (items: NewsItem[], maxItems: number): NewsItem[] => {
  if (items.length <= maxItems) return items;
  
  const sorted = sortItemsByTimestamp(items);
  return sorted.slice(0, maxItems);
};

export const useWebSocket = (url: string) => {
  const [state, setState] = useState<WebSocketState>({
    items: [],
    isConnected: false,
    isPollingActive: false,
    error: null,
    connectionStatus: 'disconnected'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
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
                // Set initial items, limiting to MAX_ITEMS_IN_STATE
                newState.items = limitItemsArray(message.items || [], MAX_ITEMS_IN_STATE);
                newState.isPollingActive = message.polling_active || false;
                console.log(`Set initial items: ${newState.items.length} items (limited from ${(message.items || []).length})`);
                break;
              
              case 'new_items':
                // Add new items to the beginning of the list and limit total
                if (message.items) {
                  const combinedItems = [...message.items, ...prev.items];
                  newState.items = limitItemsArray(combinedItems, MAX_ITEMS_IN_STATE);
                  console.log(`Added ${message.items.length} new items, total now: ${newState.items.length} (limited to ${MAX_ITEMS_IN_STATE})`);
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

  const sendMessage = useCallback((message: Record<string, unknown>) => {
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