import json
import asyncio
import logging
import sys
from pathlib import Path
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import paho.mqtt.client as mqtt
from datetime import datetime

# Add project root to path for config import
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import get_config, get_mqtt_topics
except ImportError:
    print("Error: Could not import config. Make sure config.py exists in the project root.")
    sys.exit(1)

# Configure logging
config = get_config()
logging.basicConfig(level=getattr(logging, config.log_level.upper()), format=config.log_format)
logger = logging.getLogger(__name__)

# Get configuration
TEAM_ID = config.team_id
topics = get_mqtt_topics()
MQTT_TOPIC = topics["movement"]
MQTT_HEARTBEAT_TOPIC = topics["heartbeat"]
MQTT_BROKER = config.mqtt_broker
MQTT_PORT = config.mqtt_port
WEBSOCKET_PORT = config.websocket_port

# FastAPI app
app = FastAPI(title="Face Tracking Backend", version="1.0.0")

# WebSocket connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_count = 0
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_count += 1
        logger.info(f"Browser connected. Total clients: {self.client_count}")
        
        # Send initial status
        await self.send_personal_message({
            "type": "connection_status",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "clients": self.client_count
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.client_count -= 1
            logger.info(f"Browser disconnected. Total clients: {self.client_count}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(connection)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)

manager = ConnectionManager()

# MQTT Client setup
class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client()
        self.connected = False
        self.setup_callbacks()
        
    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            
            # Subscribe to topics
            client.subscribe(MQTT_TOPIC)
            client.subscribe(MQTT_HEARTBEAT_TOPIC)
            logger.info(f"Subscribed to topics: {MQTT_TOPIC}, {MQTT_HEARTBEAT_TOPIC}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Add metadata
            message = {
                "type": "mqtt_message",
                "topic": topic,
                "payload": payload,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to all WebSocket clients
            asyncio.run(manager.broadcast(message))
            
            # Log the message
            if "movement" in topic:
                status = payload.get("status", "UNKNOWN")
                confidence = payload.get("confidence", 0)
                logger.info(f"Movement update: {status} (confidence: {confidence:.2f})")
            elif "heartbeat" in topic:
                node = payload.get("node", "unknown")
                status = payload.get("status", "UNKNOWN")
                logger.debug(f"Heartbeat from {node}: {status}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def connect(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            logger.info("MQTT client started")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            raise
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client stopped")

mqtt_manager = MQTTManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types from client
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                elif message.get("type") == "get_status":
                    await manager.send_personal_message({
                        "type": "status_response",
                        "mqtt_connected": mqtt_manager.connected,
                        "clients": manager.client_count,
                        "team_id": TEAM_ID,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON from WebSocket client")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# HTTP endpoints
@app.get("/")
async def root():
    return {
        "message": "Face Tracking Backend API",
        "version": "1.0.0",
        "team_id": TEAM_ID,
        "status": "running",
        "websocket_endpoint": f"/ws",
        "mqtt_connected": mqtt_manager.connected
    }

@app.get("/status")
async def get_status():
    return {
        "mqtt_connected": mqtt_manager.connected,
        "websocket_clients": manager.client_count,
        "team_id": TEAM_ID,
        "mqtt_topics": [MQTT_TOPIC, MQTT_HEARTBEAT_TOPIC],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mqtt_connected": mqtt_manager.connected,
        "timestamp": datetime.now().isoformat()
    }

# Serve static files (web dashboard)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the web dashboard"""
    try:
        dashboard_file = Path(__file__).parent / "static" / "index.html"
        with open(dashboard_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Dashboard Not Found</title></head>
            <body>
                <h1>Dashboard Not Available</h1>
                <p>The web dashboard file is missing. Please ensure static/index.html exists.</p>
            </body>
        </html>
        """)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Face Tracking Backend...")
    
    # Connect to MQTT broker
    try:
        mqtt_manager.connect()
        logger.info("Backend started successfully")
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Face Tracking Backend...")
    mqtt_manager.disconnect()
    logger.info("Backend shutdown complete")

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting backend server on port {WEBSOCKET_PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=WEBSOCKET_PORT,
        reload=False,
        log_level="info"
    )
