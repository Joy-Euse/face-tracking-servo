#!/usr/bin/env python3
"""
Vision Node Startup Script with Configuration Management
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config import config_manager, get_config
except ImportError as e:
    print(f"Error importing configuration: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

def setup_logging():
    """Setup logging configuration"""
    config = get_config()
    
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format
    )

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="Face Tracking Vision Node")
    parser.add_argument("--team-id", help="Override team identifier")
    parser.add_argument("--mqtt-broker", help="Override MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, help="Override MQTT broker port")
    parser.add_argument("--camera-id", type=int, help="Override camera device ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", action="store_true", help="Show configuration and exit")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    
    # Apply command line overrides
    config = get_config()
    if args.team_id:
        config.team_id = args.team_id
    if args.mqtt_broker:
        config.mqtt_broker = args.mqtt_broker
    if args.mqtt_port:
        config.mqtt_port = args.mqtt_port
    if args.camera_id:
        config.camera_id = args.camera_id
    if args.debug:
        config.log_level = "DEBUG"
    
    # Validate configuration
    if not config_manager.validate():
        print("❌ Configuration validation failed. Please check your settings.")
        sys.exit(1)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Show configuration if requested
    if args.config:
        config_manager.print_config()
        sys.exit(0)
    
    # Print configuration
    config_manager.print_config()
    
    # Import and run the vision node
    try:
        from vision_node import VisionNode, TrackingConfig
        
        # Create tracking config from system config
        tracking_config = TrackingConfig(
            team_id=config.team_id,
            mqtt_broker=config.mqtt_broker,
            mqtt_port=config.mqtt_port,
            camera_id=config.camera_id,
            frame_width=config.frame_width,
            frame_height=config.frame_height,
            detection_confidence=config.detection_confidence,
            tracking_confidence=config.tracking_confidence,
            center_threshold=config.center_threshold,
            publish_interval=config.publish_interval
        )
        
        # Create and run vision node
        node = VisionNode(tracking_config)
        logger.info("Starting vision node...")
        node.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start vision node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
