# 📈 Stock-x - Real-time NSE Announcements Tracker

> 🚀 A powerful FastAPI-based real-time NSE announcements tracking system with WebSocket support

## 📸 Screenshots

### Main Dashboard
![Stock-x Dashboard](screenshots/image_1.png)

### Real-time Updates
![Live Announcements](screenshots/image_2.png)

---

## ✨ Features

- **⚡ Real-time WebSocket Communication**: Get live updates of new announcements instantly
- **🔌 REST API**: Full REST endpoints for programmatic access to announcements  
- **💾 Database Storage**: Persistent SQLite storage with optimized indexing
- **🔄 Background Polling**: Automatic monitoring of NSE RSS feeds every 5 seconds
- **🛡️ Duplicate Detection**: Intelligent duplicate prevention using content identifiers
- **🤖 Browser Automation**: Uses SeleniumBase with undetected Chrome for reliable RSS feed access
- **🌐 CORS Support**: Allows connections from any origin for easy frontend integration
- **📦 Executable Support**: Can be packaged as a standalone executable with auto-py-to-exe
- **⚡ Memory Optimization**: Efficient caching and database cleanup

## 📋 Requirements

- 🐍 Python 3.8+
- 🏠 Virtual environment (recommended)
- 🌐 Chrome browser (for SeleniumBase automation)

## 🚀 Installation

1. **📂 Clone or download the project**

2. **📦 Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **▶️ Run the application**:
   ```bash
   python main.py
   ```

The database will be created automatically on first run in the same directory as the executable/script.

## 💻 Usage

### 🏁 Starting the Server

**Option 1: Run as Python script**
```bash
python main.py
```

**Option 2: Run FastAPI server directly**
```bash
python fastapi_server.py
```

**Option 3: Create and run executable**
Use auto-py-to-exe to create a standalone executable that can run without Python installed.

The server will start and be available at:
- 🌐 Main API: http://localhost:5127
- 🔌 WebSocket Endpoint: ws://localhost:5127/ws  
- 📚 API Documentation: http://localhost:5127/docs
- ❤️ Health Check: http://localhost:5127/health

### 🔧 Building Executable

To create a standalone executable:

1. Install auto-py-to-exe: `pip install auto-py-to-exe`
2. Run: `auto-py-to-exe`
3. Configure:
   - Script Location: `main.py`
   - One File: Yes
   - Console Window: Yes (to see logs)
   - Additional Files: Include any required files

The executable will create the database (`seen_items.db`) in the same directory as the .exe file.

## 🛠️ API Endpoints

### 🔗 REST Endpoints

| Method | Endpoint | Description | 
|--------|----------|-------------|
| GET    | `/` | 📋 API information and version |
| GET    | `/items` | 📊 Get latest 100 items from database (sorted by date) |
| GET    | `/status` | 📈 Get polling status and connection count |
| GET    | `/health` | ❤️ Health check endpoint |
| POST   | `/start-polling` | ▶️ Start background polling for new items |
| POST   | `/stop-polling` | ⏹️ Stop background polling |

### 🔌 WebSocket Endpoint

- **🌐 URL**: `ws://localhost:5127/ws`
- **📡 Protocol**: JSON messages

#### 📨 WebSocket Message Types

**From Server to Client:**

```json
{
  "type": "initial_data",
  "items": [...],
  "count": 10,
  "polling_active": true,
  "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
  "timestamp": "2025-01-18T10:30:00Z"
}
```

```json
{
  "type": "new_items", 
  "items": [...],
  "count": 3,
  "timestamp": "2025-01-18T10:31:00Z"
}
```

```json
{
  "type": "status_update",
  "polling_active": true,
  "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
  "timestamp": "2025-01-18T10:32:00Z"
}
```

**From Client to Server:**

```json
{"type": "ping"}
```

```json
{"type": "get_status"}
```

## 🎨 Frontend Integration

This FastAPI server is designed to work with any frontend framework. Here are examples:

### ⚛️ React Integration

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:5127/ws');

ws.onopen = function(event) {
    console.log('Connected to Stock-x Tracker');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'initial_data':
            // Load initial announcements
            setAnnouncements(data.items);
            break;
        case 'new_items':
            // Add new announcements
            setAnnouncements(prev => [...data.items, ...prev]);
            break;
        case 'status_update':
            setPollingActive(data.polling_active);
            break;
    }
};

// Fetch initial data via REST API
const response = await fetch('http://localhost:5127/items');
const data = await response.json();
```

### 🟨 Vanilla JavaScript Example

```javascript
const ws = new WebSocket('ws://localhost:5127/ws');

ws.onopen = function(event) {
    console.log('Connected to WebSocket');
    
    // Start polling automatically
    fetch('http://localhost:5127/start-polling', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
    });
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'new_items') {
        data.items.forEach(item => {
            console.log(`New announcement: ${item.title}`);
            // Update your UI here
        });
    }
};
```

## ⚙️ Configuration

### 🔧 Default Settings

- **🌐 Server**: localhost:5127
- **⏰ Polling Interval**: 5 seconds
- **📡 RSS URL**: `https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml`
- **💾 Database**: SQLite (`seen_items.db` in application directory)
- **📊 Max Stored Items**: 100 (configurable)
- **🧠 Memory Cache**: 500 identifiers for fast duplicate detection

### 🎛️ Customization

You can modify these settings in the source files:

- **⏰ Polling interval**: Change `await asyncio.sleep(5)` in `fastapi_server.py`
- **🔌 Port**: Modify `port=5127` in `main.py` and `fastapi_server.py`
- **📊 Max items**: Adjust `MAX_STORED_IDENTIFIERS` in `tracking.py`
- **📡 RSS URL**: Change default URL in API calls

## 🗄️ Database Schema

SQLite database with optimized indexes:

```sql
CREATE TABLE seen_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    title TEXT,
    description TEXT,
    link TEXT,
    identifier TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimized indexes for performance
CREATE INDEX idx_timestamp_identifier ON seen_items(timestamp DESC, identifier);
CREATE INDEX idx_identifier ON seen_items(identifier);
CREATE INDEX idx_created_at ON seen_items(created_at DESC);
```

## 🏗️ Architecture

### 🧩 Components

1. **🚀 Main Entry Point** (`main.py`): Executable entry point and server orchestration
2. **🔌 FastAPI Server** (`fastapi_server.py`): REST API and WebSocket endpoints
3. **📊 Tracking Module** (`tracking.py`): RSS processing, browser automation, and database operations
4. **🔌 WebSocket Manager**: Real-time client connection management
5. **🔄 Background Polling**: Asynchronous RSS feed monitoring

### 📊 Data Flow

1. 🤖 SeleniumBase browser fetches RSS feed content (handles anti-bot measures)
2. 🔍 BeautifulSoup parses XML content for new items
3. 🛡️ Duplicate detection using content-based identifiers
4. 💾 New items saved to SQLite database with batch operations
5. 📡 Real-time broadcast to all connected WebSocket clients
6. 🔌 REST API provides access to stored announcements

## 🤖 Browser Automation

Uses SeleniumBase with undetected Chrome to:
- 🛡️ Handle Cloudflare and other anti-bot protections
- 🔄 Rotate user agents automatically
- 💾 Maintain persistent browser sessions for efficiency
- 🔄 Automatically refresh browser sessions after 20 uses

## 🚨 Error Handling

- **🔌 WebSocket Disconnections**: Automatically cleaned up
- **📡 RSS Feed Errors**: Logged and broadcast to clients with error messages
- **💾 Database Errors**: Graceful handling with transaction rollbacks
- **🤖 Browser Errors**: Automatic browser session reinitialization
- **🛡️ Duplicate Items**: Efficiently handled using unique constraints

## ⚡ Performance Optimizations

- **📦 Batch Database Operations**: Multiple items inserted in single transaction
- **🧠 Memory Caching**: Recent identifiers cached for O(1) duplicate detection
- **🚪 Early Exit**: Stops processing when consecutive known items found
- **💾 Persistent Browser**: Reuses browser sessions to avoid initialization overhead
- **📊 Database Indexing**: Optimized indexes for fast queries

## 🔧 Troubleshooting

### ⚠️ Common Issues

1. **🔌 Port 5127 already in use**:
   ```bash
   # Windows
   netstat -ano | findstr :5127
   # Kill process if needed
   taskkill /PID <PID> /F
   ```

2. **💾 Database location issues with executable**:
   - Database is created in same directory as .exe file
   - Check logs for actual database path
   - Ensure write permissions in executable directory

3. **🤖 Browser automation fails**:
   - Ensure Chrome browser is installed
   - Check if antivirus is blocking browser automation
   - Try running as administrator

4. **📡 No new items detected**:
   - Check if polling is active via `/status` endpoint
   - Verify RSS feed is accessible in browser
   - Check server logs for parsing errors

### 🐛 Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deployment

### 🏠 Local Development
```bash
python main.py
```

### 🌐 Production Deployment
```bash
# Using uvicorn directly
uvicorn fastapi_server:app --host 0.0.0.0 --port 5127

# Using Docker (create Dockerfile as needed)
# Using systemd service (Linux)
# Using Windows Service (Windows)
```

### 📦 Standalone Executable
- Use auto-py-to-exe to create distributable executable
- Database and logs will be created in executable directory
- No Python installation required on target machine

## 📄 License

This project is provided as-is for educational and development purposes. 