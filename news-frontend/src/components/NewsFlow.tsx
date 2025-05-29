import { useRef, useState, useEffect } from 'react';
import { NewsItem } from './NewsItem';
import type { NewsItem as NewsItemType } from '../hooks/useWebSocket';
import './NewsFlow.css';

interface NewsFlowProps {
  items: NewsItemType[];
  isConnected: boolean;
}

export const NewsFlow: React.FC<NewsFlowProps> = ({ items, isConnected }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [seenItems, setSeenItems] = useState<Set<string>>(new Set());
  const [highlightedItems, setHighlightedItems] = useState<Map<string, 'green' | 'red'>>(new Map());
  const colorToggleRef = useRef<'green' | 'red'>('green');
  const [userScrolledPastTenItems, setUserScrolledPastTenItems] = useState(false);

  // Effect to handle scroll and decide visibility of scroll-to-top button
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      if (items.length < 10) {
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
  }, [items.length]); // Rerun when item count changes, especially around the 10 item threshold

  // Track new items and apply highlighting
  useEffect(() => {
    if (items.length === 0) return;

    const newItemIdentifiers: string[] = [];
    
    // Find truly new items that haven't been seen before
    items.forEach(item => {
      if (!seenItems.has(item.identifier)) {
        newItemIdentifiers.push(item.identifier);
      }
    });

    if (newItemIdentifiers.length > 0) {
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
  }, [items, seenItems]);

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

  if (items.length === 0) {
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
        {items.map((item) => (
          <NewsItem
            key={item.identifier}
            item={item}
            highlightColor={highlightedItems.get(item.identifier) || null}
          />
        ))}
      </div>
      
      {items.length >= 10 && userScrolledPastTenItems && (
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
    </div>
  );
}; 