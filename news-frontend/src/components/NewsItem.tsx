import type { NewsItem as NewsItemType } from '../hooks/useWebSocket';
import './NewsItem.css';

interface NewsItemProps {
  item: NewsItemType;
  highlightColor?: 'green' | 'red' | null;
}

export const NewsItem: React.FC<NewsItemProps> = ({ item, highlightColor }) => {
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const today = new Date();
      
      // Check if it's today (same year, month, and day)
      const isToday = date.getFullYear() === today.getFullYear() &&
                     date.getMonth() === today.getMonth() &&
                     date.getDate() === today.getDate();
      
      if (isToday) {
        // Show only time for today
        return date.toLocaleString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });
      } else {
        // Show date without year for other days
        return date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });
      }
    } catch {
      return timestamp;
    }
  };

  const handleItemClick = () => {
    if (item.link) {
      window.open(item.link, '_blank', 'noopener,noreferrer');
    }
  };

  const getItemClassName = () => {
    let className = 'news-item';
    if (highlightColor === 'green') {
      className += ' news-item--highlight-green';
    } else if (highlightColor === 'red') {
      className += ' news-item--highlight-red';
    }
    return className;
  };

  return (
    <div 
      className={getItemClassName()}
      onClick={handleItemClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleItemClick();
        }
      }}
    >
      <div className="news-item__header">
        <h3 className="news-item__title">{item.title}</h3>
        <time className="news-item__timestamp">
          {formatTimestamp(item.timestamp)}
        </time>
      </div>
      
      <div className="news-item__description">
        {item.description}
      </div>
      
      {item.link && (
        <div className="news-item__footer">
          <span className="news-item__link-indicator">
            Click to view details →
          </span>
        </div>
      )}
    </div>
  );
}; 