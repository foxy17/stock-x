# NSE Tracker - Standalone Executable

This guide helps you create a standalone executable for the NSE Announcements Tracker that React applications can connect to locally.

## 🚀 Quick Start

### Building the Executable

1. **Ensure auto-py-to-exe is installed:**
   ```bash
   pip install auto-py-to-exe
   ```

2. **Run the build script:**
   ```bash
   # On Windows
   build_executable.bat
   
   # Or manually
   auto-py-to-exe --config build_config.json --no-ui
   ```

3. **Find your executable:**
   - Location: `./dist/NSE-Tracker-Server/`
   - File: `NSE-Tracker-Server.exe`

### Running the Executable

1. **Navigate to the dist folder:**
   ```
   cd dist/NSE-Tracker-Server/
   ```

2. **Run the executable:**
   ```
   NSE-Tracker-Server.exe
   ```

3. **Server will start on:**
   - **API URL:** `http://localhost:5127`
   - **WebSocket:** `ws://localhost:5127/ws`

## 🔌 Connecting from React

### REST API Example
```javascript
// Fetch all items
const response = await fetch('http://localhost:5127/items');
const data = await response.json();
console.log('NSE Items:', data.items);

// Start polling
await fetch('http://localhost:5127/start-polling', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
  })
});
```

### WebSocket Example
```javascript
const ws = new WebSocket('ws://localhost:5127/ws');

ws.onopen = () => {
  console.log('Connected to NSE Tracker');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'new_items') {
    console.log('New NSE announcements:', data.items);
    // Update your React state here
  }
  
  if (data.type === 'initial_data') {
    console.log('Initial NSE data:', data.items);
    // Set initial React state here
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### React Hook Example
```javascript
import { useState, useEffect } from 'react';

const useNSETracker = () => {
  const [items, setItems] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:5127/ws');
    
    websocket.onopen = () => {
      setIsConnected(true);
      console.log('Connected to NSE Tracker');
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_items') {
        setItems(prev => [...data.items, ...prev]);
      }
      
      if (data.type === 'initial_data') {
        setItems(data.items);
      }
    };
    
    websocket.onclose = () => {
      setIsConnected(false);
      console.log('Disconnected from NSE Tracker');
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, []);

  const startPolling = async () => {
    await fetch('http://localhost:5127/start-polling', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
      })
    });
  };

  const stopPolling = async () => {
    await fetch('http://localhost:5127/stop-polling', {
      method: 'POST'
    });
  };

  return {
    items,
    isConnected,
    startPolling,
    stopPolling
  };
};

export default useNSETracker;
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/items` | Get all stored items |
| GET | `/status` | Get server status |
| GET | `/health` | Health check |
| POST | `/start-polling` | Start polling for new items |
| POST | `/stop-polling` | Stop polling |
| WS | `/ws` | WebSocket for real-time updates |

## 🎯 Features

- ✅ **Standalone Executable** - No Python installation needed on client machines
- ✅ **Cross-Origin Support** - CORS enabled for React apps
- ✅ **Real-time Updates** - WebSocket support for live data
- ✅ **RESTful API** - Standard HTTP endpoints
- ✅ **Persistent Storage** - SQLite database for seen items
- ✅ **Error Handling** - Robust error handling and logging
- ✅ **Browser Integration** - Automatically opens browser on start

## 🔧 Configuration

### Custom Port/Host
Edit `main.py` and change:
```python
server = NSETrackerServer(host="localhost", port=5127)
```

### Custom RSS URL
The default URL is NSE announcements, but you can change it by sending a POST to `/start-polling` with a custom URL:
```javascript
await fetch('http://localhost:5127/start-polling', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: "your-custom-rss-url.xml"
  })
});
```

## 📦 Distribution

The executable is completely standalone and includes:
- Python runtime
- All dependencies (FastAPI, Uvicorn, SeleniumBase, etc.)
- Your application code
- SQLite database support

You can distribute the entire `./dist/NSE-Tracker-Server/` folder to users.

## 🐛 Troubleshooting

### Port Already in Use
If port 5127 is busy, the server will fail to start. Change the port in `main.py` and rebuild.

### Antivirus Warnings
Some antivirus software may flag the executable. This is common with PyInstaller-built executables. You may need to:
- Add an exception for the executable
- Use the `--build-directory-override` option in auto-py-to-exe

### CORS Issues
The server has CORS enabled for all origins (`*`). If you still have CORS issues, ensure your React app is making requests to the correct URL (`http://localhost:5127`).

### WebSocket Connection Issues
Ensure:
- Server is running (`http://localhost:5127/health` should respond)
- No firewall blocking the connection
- Correct WebSocket URL (`ws://localhost:5127/ws`)

## 📋 Build Requirements

- Python 3.6+
- auto-py-to-exe 2.46.0+
- All dependencies from requirements.txt
- Windows (for .exe), Linux/Mac support available

## 🎉 Success!

Once built, your executable provides a complete NSE announcements API server that React applications can connect to for real-time stock market updates! 