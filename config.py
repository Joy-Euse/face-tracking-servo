"""
Centralized Configuration Management for Face Tracking System
This module provides configuration settings for all components of the distributed system
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SystemConfig:
    """Main system configuration"""
    team_id: str = "Joyeuse01"
    phase: str = "phase1"  # phase1 (open-loop) or phase2 (closed-loop)
    
    # MQTT Configuration
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_keepalive: int = 60
    
    # WebSocket Configuration
    websocket_port: int = 9002
    websocket_host: str = "0.0.0.0"
    
    # Vision Node Configuration
    camera_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    detection_confidence: float = 0.5
    tracking_confidence: float = 0.5
    center_threshold: float = 0.15  # 15% of frame width from center
    publish_interval: float = 0.1  # 100ms between messages
    
    # Servo Configuration (for ESP8266 reference)
    servo_pin: int = 5  # GPIO5 / D1
    servo_center: int = 90
    servo_step_size: int = 2
    servo_min_angle: int = 30
    servo_max_angle: int = 150
    servo_min_pulse: int = 500
    servo_max_pulse: int = 2400
    
    # Timing Configuration
    heartbeat_interval: int = 30  # seconds
    connection_retry_interval: int = 5  # seconds
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self):
        self.config = SystemConfig()
        self.load_from_env()
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        # System settings
        self.config.team_id = os.getenv("TEAM_ID", self.config.team_id)
        self.config.phase = os.getenv("SYSTEM_PHASE", self.config.phase)
        
        # MQTT settings
        self.config.mqtt_broker = os.getenv("MQTT_BROKER", self.config.mqtt_broker)
        self.config.mqtt_port = int(os.getenv("MQTT_PORT", str(self.config.mqtt_port)))
        self.config.mqtt_username = os.getenv("MQTT_USERNAME", self.config.mqtt_username)
        self.config.mqtt_password = os.getenv("MQTT_PASSWORD", self.config.mqtt_password)
        
        # WebSocket settings
        self.config.websocket_port = int(os.getenv("WEBSOCKET_PORT", str(self.config.websocket_port)))
        self.config.websocket_host = os.getenv("WEBSOCKET_HOST", self.config.websocket_host)
        
        # Vision settings
        self.config.camera_id = int(os.getenv("CAMERA_ID", str(self.config.camera_id)))
        self.config.frame_width = int(os.getenv("FRAME_WIDTH", str(self.config.frame_width)))
        self.config.frame_height = int(os.getenv("FRAME_HEIGHT", str(self.config.frame_height)))
        self.config.detection_confidence = float(os.getenv("DETECTION_CONFIDENCE", str(self.config.detection_confidence)))
        self.config.tracking_confidence = float(os.getenv("TRACKING_CONFIDENCE", str(self.config.tracking_confidence)))
        self.config.center_threshold = float(os.getenv("CENTER_THRESHOLD", str(self.config.center_threshold)))
        self.config.publish_interval = float(os.getenv("PUBLISH_INTERVAL", str(self.config.publish_interval)))
        
        # Logging
        self.config.log_level = os.getenv("LOG_LEVEL", self.config.log_level)
    
    def get_mqtt_topics(self) -> dict:
        """Get MQTT topics for this team"""
        base_topic = f"vision/{self.config.team_id}"
        return {
            "movement": f"{base_topic}/movement",
            "heartbeat": f"{base_topic}/heartbeat",
            "base": base_topic
        }
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for dashboard"""
        return f"ws://localhost:{self.config.websocket_port}/ws"
    
    def get_backend_url(self) -> str:
        """Get backend URL for API"""
        return f"http://localhost:{self.config.websocket_port}"
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        # Validate team ID
        if not self.config.team_id or not self.config.team_id.replace("_", "").replace("-", "").isalnum():
            errors.append("Team ID must be alphanumeric (underscores and hyphens allowed)")
        
        # Validate ports
        if not (1 <= self.config.mqtt_port <= 65535):
            errors.append("MQTT port must be between 1 and 65535")
        
        if not (1 <= self.config.websocket_port <= 65535):
            errors.append("WebSocket port must be between 1 and 65535")
        
        # Validate vision settings
        if not (0.0 <= self.config.detection_confidence <= 1.0):
            errors.append("Detection confidence must be between 0.0 and 1.0")
        
        if not (0.0 <= self.config.tracking_confidence <= 1.0):
            errors.append("Tracking confidence must be between 0.0 and 1.0")
        
        if not (0.0 <= self.config.center_threshold <= 0.5):
            errors.append("Center threshold must be between 0.0 and 0.5")
        
        if not (0.01 <= self.config.publish_interval <= 1.0):
            errors.append("Publish interval must be between 0.01 and 1.0 seconds")
        
        # Validate servo settings
        if not (0 <= self.config.servo_center <= 180):
            errors.append("Servo center must be between 0 and 180 degrees")
        
        if not (0 <= self.config.servo_min_angle < self.config.servo_max_angle <= 180):
            errors.append("Servo angle limits must be valid (min < max, both within 0-180)")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def print_config(self):
        """Print current configuration"""
        print("=== Face Tracking System Configuration ===")
        print(f"Team ID: {self.config.team_id}")
        print(f"Phase: {self.config.phase}")
        print()
        print("MQTT Configuration:")
        print(f"  Broker: {self.config.mqtt_broker}:{self.config.mqtt_port}")
        topics = self.get_mqtt_topics()
        print(f"  Movement Topic: {topics['movement']}")
        print(f"  Heartbeat Topic: {topics['heartbeat']}")
        print()
        print("WebSocket Configuration:")
        print(f"  Host: {self.config.websocket_host}")
        print(f"  Port: {self.config.websocket_port}")
        print()
        print("Vision Configuration:")
        print(f"  Camera ID: {self.config.camera_id}")
        print(f"  Frame Size: {self.config.frame_width}x{self.config.frame_height}")
        print(f"  Detection Confidence: {self.config.detection_confidence}")
        print(f"  Center Threshold: {self.config.center_threshold}")
        print(f"  Publish Interval: {self.config.publish_interval}s")
        print()
        print("Servo Configuration:")
        print(f"  Pin: {self.config.servo_pin}")
        print(f"  Center: {self.config.servo_center}°")
        print(f"  Range: {self.config.servo_min_angle}° - {self.config.servo_max_angle}°")
        print(f"  Step Size: {self.config.servo_step_size}°")
        print("==========================================")

# Global configuration instance
config_manager = ConfigManager()

def get_config() -> SystemConfig:
    """Get the global configuration instance"""
    return config_manager.config

def get_mqtt_topics() -> dict:
    """Get MQTT topics for the current team"""
    return config_manager.get_mqtt_topics()

if __name__ == "__main__":
    # Test configuration
    config_manager.print_config()
    
    if config_manager.validate():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors")
