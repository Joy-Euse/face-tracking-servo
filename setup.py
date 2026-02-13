#!/usr/bin/env python3
"""
Setup Script for Face Tracking System
Installs dependencies and configures the system
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description, check=True):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr}")
        return False

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_python_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    
    # Upgrade pip
    run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip", check=False)
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        return False
    
    # Install additional dependencies for setup
    setup_deps = ["python-dotenv", "websocket-client", "requests"]
    for dep in setup_deps:
        run_command(f"{sys.executable} -m pip install {dep}", f"Installing {dep}", check=False)
    
    return True

def setup_mqtt_broker():
    """Setup MQTT broker"""
    print("\n📡 Setting up MQTT broker...")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Try to install mosquitto
        if run_command("which mosquitto", "Checking for mosquitto", check=False):
            print("✅ Mosquitto already installed")
        else:
            print("Installing mosquitto...")
            if run_command("sudo apt-get update && sudo apt-get install -y mosquitto mosquitto-clients", 
                          "Installing mosquitto"):
                print("✅ Mosquitto installed successfully")
            else:
                print("⚠️  Could not install mosquitto automatically")
                print("   Please install manually: sudo apt-get install mosquitto mosquitto-clients")
                return False
        
        # Start and enable mosquitto service
        run_command("sudo systemctl start mosquitto", "Starting mosquitto service", check=False)
        run_command("sudo systemctl enable mosquitto", "Enabling mosquitto service", check=False)
        
    elif system == "windows":
        print("⚠️  Windows detected")
        print("   Please download and install Mosquitto manually:")
        print("   https://mosquitto.org/download/")
        print("   After installation, start the Mosquitto service")
        
    elif system == "darwin":  # macOS
        if run_command("which mosquitto", "Checking for mosquitto", check=False):
            print("✅ Mosquitto already installed")
        else:
            print("Installing mosquitto with Homebrew...")
            if run_command("brew install mosquitto", "Installing mosquitto"):
                print("✅ Mosquitto installed successfully")
            else:
                print("⚠️  Could not install mosquitto automatically")
                print("   Please install manually: brew install mosquitto")
                return False
    
    return True

def create_env_file():
    """Create .env file from template"""
    print("\n⚙️  Setting up configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        overwrite = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if overwrite.lower() != 'y':
            print("Skipping configuration setup")
            return True
    
    if env_example.exists():
        # Copy example to .env
        with open(env_example, 'r') as f:
            content = f.read()
        
        # Get user input for team ID
        default_team = "Joyeuse01"
        team_id = input(f"Enter your team ID (default: {default_team}): ").strip()
        if not team_id:
            team_id = default_team
        
        # Replace team ID in content
        content = content.replace("TEAM_ID=Joyeuse01", f"TEAM_ID={team_id}")
        
        # Write .env file
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Configuration created with team ID: {team_id}")
        return True
    else:
        print("⚠️  .env.example file not found")
        return False

def test_installation():
    """Test the installation"""
    print("\n🧪 Testing installation...")
    
    # Test Python imports
    try:
        import cv2
        import mediapipe as mp
        import paho.mqtt.client as mqtt
        import fastapi
        print("✅ All major libraries imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test configuration
    try:
        from config import config_manager
        if config_manager.validate():
            print("✅ Configuration validation passed")
        else:
            print("⚠️  Configuration has issues (may need manual adjustment)")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    return True

def print_next_steps():
    """Print next steps"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Start MQTT broker (if not already running)")
    print("2. Start the backend service:")
    print("   python start_backend.py")
    print("3. Start the vision node:")
    print("   python start_vision.py")
    print("4. Upload ESP8266 code (see esp8266_controller/README.md)")
    print("5. Open the web dashboard:")
    print("   http://localhost:9002/dashboard")
    print("\n🧪 Test your system:")
    print("   python test_system.py")
    print("\n📚 For detailed instructions, see README.md")
    print("="*60)

def main():
    """Main setup function"""
    print("🚀 Face Tracking System Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Setup MQTT broker
    if not setup_mqtt_broker():
        print("⚠️  MQTT broker setup incomplete - you may need to install manually")
    
    # Create configuration
    if not create_env_file():
        print("⚠️  Configuration setup incomplete")
    
    # Test installation
    if test_installation():
        print_next_steps()
    else:
        print("\n❌ Installation test failed")
        print("Please check the errors above and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()
