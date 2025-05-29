import asyncio
import logging
from typing import List, Set, Dict, Any
from datetime import datetime
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import tracking functions
try:
    from tracking import get_new_items, get_initial_items
except ImportError as e:
    print(f"Error importing from tracking.py: {e}")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global state for WebSocket connections and polling
connected_clients: List[WebSocket] = []
polling_active: bool = False
polling_url: str = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
polling_task: asyncio.Task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("FastAPI server starting up")
    yield
    # Shutdown
    global polling_active, polling_task
    logging.info("FastAPI server shutting down")
    
    # Stop polling
    polling_active = False
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    # Close all WebSocket connections
    if 'manager' in globals():
        for connection in manager.active_connections.copy():
            try:
                await connection.close()
            except Exception as e:
                logging.error(f"Error closing WebSocket connection: {e}")
    
    logging.info("Server shutdown complete")

# Initialize FastAPI app with lifespan
app = FastAPI(title="NSE Announcements Tracker API", version="1.0.0", lifespan=lifespan)

# Configure CORS to allow connections from any URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for WebSocket connections and polling
connected_clients: List[WebSocket] = []
polling_active: bool = False
polling_url: str = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
polling_task: asyncio.Task = None

# Pydantic models for API responses
class Item(BaseModel):
    timestamp: str
    title: str
    description: str
    link: str
    identifier: str

class ItemsResponse(BaseModel):
    items: List[Item]
    count: int

class StatusResponse(BaseModel):
    polling_active: bool
    connected_clients: int
    url: str

class StartPollingRequest(BaseModel):
    url: str = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"

# WebSocket manager class
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"New WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logging.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logging.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(connection)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)

    async def broadcast_json(self, data: Dict[Any, Any]):
        message = json.dumps(data)
        await self.broadcast(message)

manager = ConnectionManager()

# Background polling function
async def poll_for_new_items():
    """Background task that continuously polls for new items"""
    global polling_active
    
    while polling_active:
        try:
            logging.info(f"Polling for new items from: {polling_url}")
            new_items = get_new_items(polling_url)
            
            if new_items:
                logging.info(f"Found {len(new_items)} new items")
                
                # Format items for WebSocket transmission
                items_data = {
                    "type": "new_items",
                    "items": [
                        {
                            "timestamp": item["timestamp"],
                            "title": item["title"],
                            "description": item["description"],
                            "link": item["link"],
                            "identifier": item["identifier"]
                        }
                        for item in new_items
                    ],
                    "count": len(new_items),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Broadcast to all connected clients
                await manager.broadcast_json(items_data)
            else:
                logging.info("No new items found")
                
        except Exception as e:
            logging.error(f"Error during polling: {e}")
            error_data = {
                "type": "error",
                "message": f"Polling error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast_json(error_data)
        
        # Wait before next poll (5 seconds)
        await asyncio.sleep(5)

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "NSE Announcements Tracker API",
        "websocket_endpoint": "/ws",
        "version": "1.0.0"
    }

@app.get("/items", response_model=ItemsResponse)
async def get_items():
    """Get all items currently in the database"""
    try:
        items = get_initial_items()
        return ItemsResponse(
            items=[
                Item(
                    timestamp=item["timestamp"],
                    title=item["title"],
                    description=item["description"],
                    link=item["link"],
                    identifier=item["identifier"]
                )
                for item in items
            ],
            count=len(items)
        )
    except Exception as e:
        logging.error(f"Error getting items: {e}")
        raise

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current polling status and connection count"""
    return StatusResponse(
        polling_active=polling_active,
        connected_clients=len(manager.active_connections),
        url=polling_url
    )

@app.post("/start-polling")
async def start_polling(request: StartPollingRequest, background_tasks: BackgroundTasks):
    """Start polling for new items"""
    global polling_active, polling_url, polling_task
    
    if polling_active:
        return {"message": "Polling is already active", "status": "warning"}
    
    polling_url = request.url
    polling_active = True
    
    # Start the polling task
    polling_task = asyncio.create_task(poll_for_new_items())
    
    logging.info(f"Started polling from: {polling_url}")
    
    # Notify connected clients
    status_data = {
        "type": "status_update",
        "polling_active": True,
        "url": polling_url,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_json(status_data)
    
    return {"message": "Polling started", "url": polling_url, "status": "success"}

@app.post("/stop-polling")
async def stop_polling():
    """Stop polling for new items"""
    global polling_active, polling_task
    
    if not polling_active:
        return {"message": "Polling is not active", "status": "warning"}
    
    polling_active = False
    
    # Cancel the polling task if it exists
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    logging.info("Stopped polling")
    
    # Notify connected clients
    status_data = {
        "type": "status_update",
        "polling_active": False,
        "url": polling_url,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_json(status_data)
    
    return {"message": "Polling stopped", "status": "success"}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    
    try:
        # Send initial data to the newly connected client
        initial_items = get_initial_items()
        initial_data = {
            "type": "initial_data",
            "items": [
                {
                    "timestamp": item["timestamp"],
                    "title": item["title"],
                    "description": item["description"],
                    "link": item["link"],
                    "identifier": item["identifier"]
                }
                for item in initial_items[-10:]  # Send last 10 items
            ],
            "count": len(initial_items[-10:]),
            "polling_active": polling_active,
            "url": polling_url,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(initial_data), websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive message from client (could be ping, status request, etc.)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    # Respond to ping with pong
                    pong_response = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(pong_response), websocket)
                
                elif message.get("type") == "get_status":
                    # Send current status
                    status_response = {
                        "type": "status_response",
                        "polling_active": polling_active,
                        "connected_clients": len(manager.active_connections),
                        "url": polling_url,
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(status_response), websocket)
                
                else:
                    # Echo unknown messages
                    echo_response = {
                        "type": "echo",
                        "original_message": message,
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(echo_response), websocket)
                    
            except json.JSONDecodeError:
                # Handle non-JSON messages
                echo_response = {
                    "type": "echo",
                    "original_message": data,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(echo_response), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "polling_active": polling_active,
        "connected_clients": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    
    # Start the server
    uvicorn.run(
        "fastapi_server:app",
        host="localhost",
        port=5127,
        reload=True,
        log_level="info"
    ) 