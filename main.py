#!/usr/bin/env python3
"""
NSE Stock Tracker - Standalone Executable Entry Point

This script creates a standalone executable that runs the FastAPI server locally.
React applications can connect to this localhost server to get real-time NSE announcements.
"""

import sys
import os
import asyncio
import logging
import threading
import time
import webbrowser
from pathlib import Path

# Add the current directory to Python path to ensure imports work
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

try:
    import uvicorn
    from fastapi_server import app
    from tracking import get_initial_items, get_new_items
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed.")
    input("Press Enter to exit...")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('nse_tracker.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

class NSETrackerServer:
    def __init__(self, host="localhost", port=5127):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
    def start_server(self):
        """Start the FastAPI server in a separate thread"""
        try:
            logger.info(f"Starting NSE Tracker Server on {self.host}:{self.port}")
            logger.info("=" * 50)
            logger.info("NSE ANNOUNCEMENTS TRACKER")
            logger.info("=" * 50)
            logger.info(f"Server URL: http://{self.host}:{self.port}")
            logger.info(f"WebSocket URL: ws://{self.host}:{self.port}/ws")
            logger.info(f"API Endpoints:")
            logger.info(f"  - GET  /items          - Get all items")
            logger.info(f"  - GET  /status         - Get server status")
            logger.info(f"  - POST /start-polling  - Start polling for new items")
            logger.info(f"  - POST /stop-polling   - Stop polling")
            logger.info(f"  - GET  /health         - Health check")
            logger.info("=" * 50)
            
            # Test initial functionality
            logger.info("Testing initial functionality...")
            initial_items = get_initial_items()
            logger.info(f"Database contains {len(initial_items)} items")
            
            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            
            self.server = uvicorn.Server(config)
            self.running = True
            
            # Run the server
            self.server.run()
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            self.running = False
            
    def start_in_thread(self):
        """Start the server in a background thread"""
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        # Wait a moment for server to start
        time.sleep(2)
        
        return self.running
        
    def stop_server(self):
        """Stop the server"""
        if self.server:
            logger.info("Stopping server...")
            self.running = False
            self.server.should_exit = True

def open_browser(url, delay=3):
    """Open browser after a delay"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
        logger.info(f"Opened browser to {url}")
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")

def main():
    """Main entry point for the executable"""
    print("Server will start on: http://localhost:5127")
    print("WebSocket endpoint: ws://localhost:5127/ws")
    print()
    print("=" * 60)
    
    # Create server instance
    server = NSETrackerServer()
    
    try:
        # Start server
        if server.start_in_thread():
            print("✅ Server started successfully!")
            print()
            print("Available endpoints:")
            print("  🌐 Main API: http://localhost:5127")
            print("  📡 WebSocket: ws://localhost:5127/ws")
            print("  📊 Status: http://localhost:5127/status")
            print("  💓 Health: http://localhost:5127/health")
            print()
            print("To connect your React app, use:")
            print("  Fetch API: fetch('http://localhost:5127/items')")
            print("  WebSocket: new WebSocket('ws://localhost:5127/ws')")
            print()
            print("Press Ctrl+C to stop the server")
            print("=" * 60)
            
            # Optional: Open browser to API documentation
            browser_thread = threading.Thread(
                target=open_browser, 
                args=("http://localhost:5127",), 
                daemon=True
            )
            browser_thread.start()
            
            # Keep the main thread alive
            try:
                while server.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️  Shutdown requested by user...")
                
        else:
            print("❌ Failed to start server!")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Fatal error: {e}")
        return 1
        
    finally:
        # Cleanup
        server.stop_server()
        print("✅ Server stopped. Thank you for using NSE Tracker!")
        
    return 0

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(current_dir)
    
    # Run main function
    exit_code = main()
    
    # Keep console open for a moment to show final message
    if exit_code != 0:
        input("\nPress Enter to exit...")
    
    sys.exit(exit_code) 