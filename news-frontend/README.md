# NSE Live News Frontend

A modern React application for displaying real-time NSE (National Stock Exchange) announcements with WebSocket connectivity.

## Features

### Real-time News Feed
- **Live WebSocket Connection**: Connects to FastAPI backend at `ws://localhost:5127/ws`
- **Automatic Reconnection**: Handles connection drops with exponential backoff
- **Connection Status Indicators**: Visual feedback for connection state and polling status

### Enhanced News Display
- **Alternating Color Highlights**: New news items alternate between **red** and **green** highlighting
- **10-Second Highlighting**: New items remain highlighted for 10 seconds
- **Animated Cards**: Beautiful gradient backgrounds with hover effects and animations
- **Click to View**: Click any news item to open the full announcement in a new tab

### Modern UI/UX
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Dark Theme**: Beautiful gradient backgrounds with glassmorphism effects
- **Smooth Animations**: Fade-in effects, pulse animations, and hover transitions
- **Custom Scrollbars**: Styled scrollbars that match the design theme
- **Auto-scroll**: Automatically scrolls to top when new items arrive

### Accessibility
- **Keyboard Navigation**: Full keyboard support with proper focus management
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **High Contrast**: Good color contrast ratios for readability

## Technology Stack

- **React 19** with TypeScript
- **Vite** for fast development and building
- **Custom Hooks** for WebSocket management
- **CSS3** with modern features (backdrop-filter, grid, flexbox)
- **ES6+ JavaScript** with async/await patterns

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running FastAPI backend on `localhost:5127`

### Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Open in browser**:
   Navigate to `http://localhost:5173` (default Vite port)

### Build for Production

```bash
npm run build
npm run preview
```

## 🚀 Deployment

### GitHub Pages Deployment
This application is configured for easy deployment to GitHub Pages.

**Quick Deploy:**
1. Ensure you're on the `main` branch
2. Push your changes - GitHub Actions will automatically deploy
3. Enable GitHub Pages in repository settings (Settings → Pages → Source: gh-pages)

**Manual Deploy:**
```bash
npm run deploy
```

📖 **For detailed deployment instructions, troubleshooting, and configuration options, see [DEPLOYMENT.md](./DEPLOYMENT.md)**

### Live Demo
Once deployed, the app will be available at:
```
https://YOUR_USERNAME.github.io/stock-x/
```

## Configuration

### WebSocket URL
The WebSocket URL is configured in `src/App.tsx`:
```typescript
const WS_URL = 'ws://localhost:5127/ws';
```

To change the backend URL, modify this constant.

### Highlight Duration
The highlighting duration can be adjusted in `src/components/NewsFlow.tsx`:
```typescript
}, 10000); // 10 seconds - change this value
```

## Component Architecture

### Core Components

1. **App.tsx** - Main application component
2. **hooks/useWebSocket.ts** - Custom hook for WebSocket management
3. **components/NewsFlow.tsx** - Manages news display and highlighting logic
4. **components/NewsItem.tsx** - Individual news item display
5. **components/StatusBar.tsx** - Connection and status information

### Key Features Implementation

#### Alternating Colors
```typescript
// In NewsFlow.tsx
colorToggleRef.current = colorToggleRef.current === 'red' ? 'green' : 'red';
```

#### WebSocket Auto-reconnection
```typescript
// Exponential backoff with max 5 attempts
const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
```

#### Responsive Design
- Mobile-first CSS approach
- Flexible layouts with CSS Grid and Flexbox
- Optimized touch targets for mobile devices

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Features Used**: WebSocket API, CSS backdrop-filter, CSS Grid, ES6 modules

## Performance Optimizations

- **React.memo**: Components are memoized where appropriate
- **useCallback**: Event handlers are memoized to prevent unnecessary re-renders
- **Efficient Re-renders**: Smart state management to minimize component updates
- **CSS Animations**: Hardware-accelerated transforms and opacity changes

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run deploy` - Deploy to GitHub Pages

### Code Style
- TypeScript strict mode enabled
- ESLint configuration for React and TypeScript
- Consistent naming conventions (camelCase for JS, kebab-case for CSS)

## Troubleshooting

### WebSocket Connection Issues
1. Ensure FastAPI backend is running on `localhost:5127`
2. Check browser console for connection errors
3. Verify CORS settings if accessing from different domain

### Performance Issues
1. Check browser DevTools for memory leaks
2. Monitor WebSocket message frequency
3. Ensure proper cleanup of event listeners

### Deployment Issues
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive troubleshooting guide
- Verify base path configuration in `vite.config.ts`
- Ensure GitHub Pages is properly configured

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for all new interfaces
3. Include responsive CSS for mobile devices
4. Test WebSocket connection edge cases
5. Update documentation when adding new features

## License

This project is part of the NSE Live News application suite.
