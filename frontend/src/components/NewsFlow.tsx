import { useRef, useState, useEffect, useMemo } from 'react';
import { NewsItem } from './NewsItem';
import type { NewsItem as NewsItemType } from '../hooks/useWebSocket';
import './NewsFlow.css';

// Constants for display limits
const MAX_DISPLAY_ITEMS = 500;

interface NewsFlowProps {
  items: NewsItemType[];
  isConnected: boolean;
}

// Utility function to sort items by timestamp (latest first)
const sortItemsByTimestamp = (items: NewsItemType[]): NewsItemType[] => {
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

export const NewsFlow: React.FC<NewsFlowProps> = ({ items, isConnected }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [seenItems, setSeenItems] = useState<Set<string>>(new Set());
  const [highlightedItems, setHighlightedItems] = useState<Map<string, 'green' | 'red'>>(new Map());
  const colorToggleRef = useRef<'green' | 'red'>('green');
  const [userScrolledPastTenItems, setUserScrolledPastTenItems] = useState(false);
  const [hasReceivedInitialData, setHasReceivedInitialData] = useState(false);
  const previousItemsLengthRef = useRef(0);

  // Memoized computation to get the latest items for display (limited to MAX_DISPLAY_ITEMS)
  const displayItems = useMemo(() => {
    if (items.length === 0) return [];
    
    // Sort items by timestamp and limit to MAX_DISPLAY_ITEMS
    const sortedItems = sortItemsByTimestamp([...items]);
    const limitedItems = sortedItems.slice(0, MAX_DISPLAY_ITEMS);
    
    console.log(`Displaying ${limitedItems.length} items (from ${items.length} total, limited to ${MAX_DISPLAY_ITEMS})`);
    return limitedItems;
  }, [items]);

  // Effect to handle scroll and decide visibility of scroll-to-top button
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      if (displayItems.length < 10) {
        setUserScrolledPastTenItems(false);
        return;
      }

      const itemsContainer = container.querySelector('.news-flow__items');
      if (!itemsContainer || itemsContainer.children.length < 10) {
        setUserScrolledPastTenItems(false);
        return;
      }
      
      const tenthItemElement = itemsContainer.children[9] as HTMLElement; // 0-indexed

      if (tenthItemElement) {
        // Check if the top of the container's scroll view is past the top of the 10th item
        const hasScrolledEnough = container.scrollTop > tenthItemElement.offsetTop;
        setUserScrolledPastTenItems(hasScrolledEnough);
      } else {
        setUserScrolledPastTenItems(false);
      }
    };

    container.addEventListener('scroll', handleScroll);
    handleScroll(); // Initial check

    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [displayItems.length]); // Use displayItems.length instead of items.length

  // Track initial data load and new items
  useEffect(() => {
    if (items.length === 0) {
      // Reset state when disconnected or no items
      setHasReceivedInitialData(false);
      setSeenItems(new Set());
      setHighlightedItems(new Map());
      previousItemsLengthRef.current = 0;
      return;
    }

    // If we haven't received initial data yet and we have items, this is the initial load
    if (!hasReceivedInitialData && items.length > 0) {
      console.log('Received initial data with', items.length, 'items');
      setHasReceivedInitialData(true);
      
      // Mark all initial items as seen without highlighting them
      const initialItemIds = new Set(items.map(item => item.identifier));
      setSeenItems(initialItemIds);
      previousItemsLengthRef.current = items.length;
      return;
    }

    // Only process new items if we've already received initial data
    if (hasReceivedInitialData) {
      const newItemIdentifiers: string[] = [];
      
      // Find truly new items that haven't been seen before
      items.forEach(item => {
        if (!seenItems.has(item.identifier)) {
          newItemIdentifiers.push(item.identifier);
        }
      });

      if (newItemIdentifiers.length > 0) {
        console.log('Found', newItemIdentifiers.length, 'new items to highlight');
        
        // Update seen items
        setSeenItems(prev => {
          const newSet = new Set(prev);
          newItemIdentifiers.forEach(id => newSet.add(id));
          return newSet;
        });

        // Apply alternating colors to new items
        setHighlightedItems(prev => {
          const newMap = new Map(prev);
          
          newItemIdentifiers.forEach(itemId => {
            newMap.set(itemId, colorToggleRef.current);
            // Toggle color for next item
            colorToggleRef.current = colorToggleRef.current === 'green' ? 'red' : 'green';
          });
          
          return newMap;
        });

        // Remove highlighting after 10 seconds
        setTimeout(() => {
          setHighlightedItems(prev => {
            const newMap = new Map(prev);
            newItemIdentifiers.forEach(itemId => {
              newMap.delete(itemId);
            });
            return newMap;
          });
        }, 10000);

        // Scroll to top to show new items
        if (containerRef.current) {
          containerRef.current.scrollTo({
            top: 0,
            behavior: 'smooth'
          });
        }
      }
    }

    previousItemsLengthRef.current = items.length;
  }, [items, seenItems, hasReceivedInitialData]);

  // Reset state when connection status changes
  useEffect(() => {
    if (!isConnected) {
      setHasReceivedInitialData(false);
      setSeenItems(new Set());
      setHighlightedItems(new Map());
      previousItemsLengthRef.current = 0;
    }
  }, [isConnected]);

  if (!isConnected) {
    return (
      <div className="news-flow news-flow--disconnected">
        <div className="news-flow__message">
          <h3>Disconnected from server</h3>
          <p>Waiting for connection to be restored...</p>
          <div className="news-flow__spinner" />
        </div>
      </div>
    );
  }

  if (displayItems.length === 0) {
    return (
      <div className="news-flow news-flow--empty">
        <div className="news-flow__message">
          <h3>No news items yet</h3>
          <p>Waiting for new announcements...</p>
          <div className="news-flow__pulse" />
        </div>
      </div>
    );
  }

  return (
    <div 
      className="news-flow" 
      ref={containerRef}
    >
      <div className="news-flow__items">
        {displayItems.map((item) => (
          <NewsItem
            key={item.identifier}
            item={item}
            highlightColor={highlightedItems.get(item.identifier) || null}
          />
        ))}
      </div>
      
      {displayItems.length >= 10 && userScrolledPastTenItems && (
        <div className="news-flow__scroll-indicator">
          <button
            className="scroll-to-top"
            onClick={() => {
              containerRef.current?.scrollTo({
                top: 0,
                behavior: 'smooth'
              });
            }}
          >
            ↑ Back to top
          </button>
        </div>
      )}
      
      {items.length > MAX_DISPLAY_ITEMS && (
        <div className="news-flow__info">
          <p style={{ 
            textAlign: 'center', 
            color: 'rgba(255, 255, 255, 0.6)', 
            fontSize: '0.85em',
            margin: '16px 0',
            fontStyle: 'italic'
          }}>
            Showing latest {MAX_DISPLAY_ITEMS} of {items.length} items
          </p>
        </div>
      )}
    </div>
  );
}; 