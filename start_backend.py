#!/usr/bin/env python3
"""
Backend Startup Script with Configuration Management
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config import config_manager, get_config
    import uvicorn
except ImportError as e:
    print(f"Error importing required modules: {e}")
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
    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    
    # Validate configuration
    if not config_manager.validate():
        print("❌ Configuration validation failed. Please check your settings.")
        sys.exit(1)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print configuration
    config_manager.print_config()
    
    # Import and run the backend
    try:
        from Backend.main import app
        
        config = get_config()
        logger.info(f"Starting backend server on {config.websocket_host}:{config.websocket_port}")
        
        uvicorn.run(
            app,
            host=config.websocket_host,
            port=config.websocket_port,
            reload=False,
            log_level=config.log_level.lower()
        )
        
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
