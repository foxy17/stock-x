import { useWebSocket } from './hooks/useWebSocket';
import { StatusBar } from './components/StatusBar';
import { NewsFlow } from './components/NewsFlow';
import './App.css';

function App() {
  const WS_URL = 'ws://localhost:5127/ws';
  const webSocketState = useWebSocket(WS_URL);

  return (
    <div className="app">
      <div className="app__container">
        <header className="app__header">
          <div className="app__header-content">
            <h1 className="app__title">
              📈 NSE Live News
            </h1>
            <p className="app__subtitle">
              Real-time National Stock Exchange announcements
            </p>
          </div>
        </header>

        <main className="app__main">
          <StatusBar 
            status={webSocketState} 
            onReconnect={webSocketState.connect}
          />
          
          <NewsFlow 
            items={webSocketState.items}
            isConnected={webSocketState.isConnected}
          />
        </main>

        <footer className="app__footer">
          <p>
            Connected to: <code>{WS_URL}</code>
          </p>
          <p>
            Built with React + TypeScript + Vite
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
