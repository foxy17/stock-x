# NSE Announcements Tracker - FastAPI Server

A FastAPI-based real-time NSE announcements tracker with WebSocket support that monitors RSS feeds for new announcements and broadcasts them to connected clients.

## Features

- **Real-time WebSocket Communication**: Get live updates of new announcements
- **Database Storage**: Persistent SQLite storage for all announcements
- **Background Polling**: Automatic monitoring of RSS feeds
- **Duplicate Detection**: Prevents duplicate announcements using composite keys
- **CORS Support**: Allows connections from any origin
- **REST API**: Full REST endpoints for programmatic access
- **Web Client**: Included HTML/JavaScript client for testing

## Requirements

- Python 3.8+
- Virtual environment (recommended)

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database** (automatic on first run):
   The SQLite database will be created automatically when you first run the tracking system.

## Usage

### Starting the Server

Run the FastAPI server on localhost:5127:

```bash
python fastapi_server.py
```

The server will start and be available at:
- API Documentation: http://localhost:5127/docs
- WebSocket Endpoint: ws://localhost:5127/ws
- Health Check: http://localhost:5127/health

### Using the Web Client

Open the included HTML client:

```bash
# Open websocket_client.html in your browser
# Or serve it with a simple HTTP server:
python -m http.server 8080
# Then visit: http://localhost:8080/websocket_client.html
```

## API Endpoints

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/` | API information |
| GET    | `/items` | Get all items from database |
| GET    | `/status` | Get polling status and connection count |
| GET    | `/health` | Health check endpoint |
| POST   | `/start-polling` | Start polling for new items |
| POST   | `/stop-polling` | Stop polling |

### WebSocket Endpoint

- **URL**: `ws://localhost:5127/ws`
- **Protocol**: JSON messages

#### WebSocket Message Types

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

## Example Usage

### Starting Polling via REST API

```bash
curl -X POST "http://localhost:5127/start-polling" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"}'
```

### WebSocket Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:5127/ws');

ws.onopen = function(event) {
    console.log('Connected to WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'initial_data':
            console.log(`Loaded ${data.count} initial items`);
            break;
        case 'new_items':
            console.log(`Received ${data.count} new items`);
            data.items.forEach(item => {
                console.log(`New: ${item.title}`);
            });
            break;
        case 'status_update':
            console.log(`Polling is now: ${data.polling_active ? 'active' : 'inactive'}`);
            break;
    }
};

// Send a ping
ws.send(JSON.stringify({type: 'ping'}));
```

### Python Client Example

```python
import asyncio
import websockets
import json

async def client():
    uri = "ws://localhost:5127/ws"
    async with websockets.connect(uri) as websocket:
        # Send a ping
        await websocket.send(json.dumps({"type": "ping"}))
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'new_items':
                print(f"New items: {len(data['items'])}")

asyncio.run(client())
```

## Configuration

### Default Settings

- **Server**: localhost:5127
- **Polling Interval**: 5 seconds
- **Default RSS URL**: NSE Announcements feed
- **Database**: SQLite (`seen_items.db`)
- **Max Stored Items**: 500

### Environment Variables

You can customize behavior by modifying the source code or by setting these variables in your environment:

- Database file location is configurable in `tracking.py`
- Polling interval can be adjusted in `fastapi_server.py`

## Database Schema

The SQLite database stores items with the following schema:

```sql
CREATE TABLE seen_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    title TEXT,
    description TEXT,
    link TEXT,
    identifier TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, title)
);
```

## Architecture

### Components

1. **FastAPI Server** (`fastapi_server.py`): Main server with REST and WebSocket endpoints
2. **Tracking Module** (`tracking.py`): RSS feed processing and database operations
3. **WebSocket Manager**: Handles multiple client connections
4. **Background Polling**: Asynchronous RSS feed monitoring

### Data Flow

1. Background task polls RSS feed every 5 seconds
2. New items are detected using composite key (timestamp + title)
3. New items are saved to SQLite database
4. All connected WebSocket clients receive new items in real-time
5. REST API provides access to stored data

## Error Handling

- **WebSocket Disconnections**: Automatically cleaned up
- **RSS Feed Errors**: Logged and broadcast to clients
- **Database Errors**: Gracefully handled with logging
- **Duplicate Items**: Silently ignored using composite unique constraint

## Security Considerations

- CORS is enabled for all origins (suitable for development)
- No authentication implemented (add as needed)
- Database uses SQLite (suitable for single-instance deployment)

## Troubleshooting

### Common Issues

1. **Port 5127 already in use**:
   ```bash
   # Change port in fastapi_server.py or kill existing process
   netstat -ano | findstr :5127
   ```

2. **WebSocket connection fails**:
   - Ensure server is running
   - Check firewall settings
   - Verify URL format

3. **No items appearing**:
   - Check if polling is active via `/status` endpoint
   - Verify RSS feed URL is accessible
   - Check server logs for errors

### Debug Mode

Run with debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration from PyQt Version

The FastAPI server replaces the PyQt desktop application with the following mapping:

| PyQt Feature | FastAPI Equivalent |
|--------------|-------------------|
| GUI List Widget | WebSocket real-time updates |
| Start/Stop Buttons | REST API endpoints |
| Status Display | WebSocket status messages |
| Item Highlighting | Client-side implementation |
| Link Opening | HTML client with clickable links |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the included HTML client
5. Submit a pull request

## License

This project is provided as-is for educational and development purposes. 