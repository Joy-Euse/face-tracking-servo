# Distributed Vision-Control System (Face-Locked Servo)

A complete distributed face tracking system that detects and tracks faces using computer vision, publishes movement commands via MQTT, and controls servo motors in real-time.

## 🎯 Project Overview

This system implements a distributed architecture with four main components:

1. **PC Vision Node** - Captures camera frames, detects faces, publishes MQTT commands
2. **ESP8266 Edge Controller** - Subscribes to MQTT, controls servo motor
3. **Backend API Service** - Hosts MQTT broker and WebSocket API
4. **Web Dashboard** - Real-time visualization of tracking status

## 🏗️ System Architecture

```
┌─────────────┐    MQTT     ┌─────────────┐    WebSocket    ┌─────────────┐
│   PC Vision │ ─────────► │   Backend   │ ─────────────► │ Web Dashboard│
│    Node     │             │   Service   │                │             │
└─────────────┘             └─────────────┘                └─────────────┘
                                      │
                                      │ MQTT
                                      ▼
                              ┌─────────────┐
                              │  ESP8266    │
                              │ Controller  │
                              └─────────────┘
```

## 📋 Requirements

### Software Dependencies
- Python 3.8+
- OpenCV 4.9+
- MediaPipe
- Paho-MQTT
- FastAPI
- NodeMCU Arduino IDE
- Mosquitto MQTT Broker

### Hardware Components
- ESP8266 (NodeMCU or Wemos D1 Mini)
- SG90 Servo Motor
- USB Camera
- 5V Power Supply (for servo)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd face-tracking-servo
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure System

```bash
# Copy environment configuration
cp .env.example .env

# Edit configuration
nano .env
```

### 4. Start MQTT Broker

```bash
# Install and start Mosquitto
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### 5. Start Backend Service

```bash
python start_backend.py
```

### 6. Start Vision Node

```bash
python start_vision.py
```

### 7. Access Web Dashboard

Open your browser and navigate to:
```
http://localhost:9002/dashboard
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your settings:

```bash
# System Configuration
TEAM_ID=Joyeuse01
SYSTEM_PHASE=phase1

# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883

# Vision Configuration
CAMERA_ID=0
DETECTION_CONFIDENCE=0.5
CENTER_THRESHOLD=0.15
```

### Team ID Configuration

Each team must use a unique `TEAM_ID` to avoid MQTT topic conflicts:

- **Good examples**: `team01`, `alpha`, `y3_grp2`
- **Bad examples**: `movement`, `servo`, generic names

## 📱 ESP8266 Setup

### 1. Install Arduino IDE
1. Download Arduino IDE 1.8.19+
2. Add ESP8266 board support:
   - File → Preferences → Additional Board Manager URLs
   - Add: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`

### 2. Install Libraries
Install these libraries via Library Manager:
- PubSubClient by Nick O'Leary
- ArduinoJson by Benoit Blanchon

### 3. Configure ESP8266
Edit `esp8266_controller/config.h`:
```cpp
#define WIFI_SSID "YourWiFiNetwork"
#define WIFI_PASSWORD "YourWiFiPassword"
#define MQTT_BROKER "192.168.1.100"  // Your MQTT broker IP
#define TEAM_ID "Joyeuse01"
```

### 4. Upload Code
1. Connect ESP8266 to computer
2. Select board: Tools → Board → ESP8266 Boards → NodeMCU 1.0
3. Upload `esp8266_controller/esp8266_servo_controller.ino`

### 5. Wiring Connections
```
ESP8266    →    Servo
D1 (GPIO5) →    Signal (Orange)
5V         →    VCC (Red)
GND        →    GND (Brown)
```

## 🎛️ Usage

### Phase 1: Open-Loop Actuation
- Camera remains fixed on PC
- Servo responds to face movement commands
- No feedback from camera position

### Phase 2: Closed-Loop Tracking
- Camera mounted on servo
- System creates true feedback loop
- Smooth tracking with minimal jitter

### Web Dashboard Features
- Real-time connection status
- Face tracking visualization
- Movement confidence indicators
- Event logging
- System information

### Command Line Options

#### Vision Node
```bash
python start_vision.py --help
python start_vision.py --team-id custom01 --debug
python start_vision.py --config  # Show configuration
```

#### Backend
```bash
python start_backend.py
```

## 📊 MQTT Topics

### Movement Commands
- **Topic**: `vision/<TEAM_ID>/movement`
- **Payload**:
```json
{
  "status": "MOVE_LEFT|MOVE_RIGHT|CENTERED|NO_FACE",
  "confidence": 0.87,
  "timestamp": 1730000000
}
```

### Heartbeat
- **Topic**: `vision/<TEAM_ID>/heartbeat`
- **Payload**:
```json
{
  "node": "pc|esp8266",
  "status": "ONLINE",
  "timestamp": 1730000000
}
```

## 🔍 Troubleshooting

### Common Issues

#### Vision Node Problems
```bash
# Check camera availability
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# Test face detection
python -c "import mediapipe as mp; print('MediaPipe OK')"
```

#### MQTT Connection Issues
```bash
# Test MQTT broker connection
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test
```

#### ESP8266 Issues
- Check WiFi credentials in `config.h`
- Verify MQTT broker IP address
- Ensure adequate power supply for servo
- Check serial monitor for debug output

#### Backend Issues
- Verify port 9002 is not in use
- Check firewall settings
- Ensure MQTT broker is running

### Debug Mode

Enable debug logging:
```bash
python start_vision.py --debug
```

### System Validation

Run configuration validation:
```bash
python config.py
```

## 📈 Performance Optimization

### Network Optimization
- Use wired Ethernet for MQTT broker
- Position ESP8266 close to WiFi access point
- Consider MQTT QoS 1 for important messages

### Vision Optimization
- Adjust detection confidence threshold
- Optimize frame resolution for your hardware
- Use GPU acceleration if available

### Servo Optimization
- Use external power supply for servo
- Add mechanical dampening
- Implement motion smoothing

## 🔒 Security Considerations

- Change default WiFi credentials
- Use MQTT authentication if broker supports it
- Consider MQTT over SSL for production
- Keep firmware updated

## 📚 API Documentation

### Backend Endpoints

#### GET `/`
System status and information

#### GET `/status`
Detailed system status

#### GET `/health`
Health check endpoint

#### WebSocket `/ws`
Real-time updates for dashboard

#### GET `/dashboard`
Web dashboard interface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of the Distributed Vision-Control System assignment.

## 🙏 Acknowledgments

- MediaPipe for face detection
- Paho MQTT for messaging
- FastAPI for backend API
- ESP8266 community for embedded support

---

**Instructor**: Gabriel Baziramwabo  
**Keywords**: Computer Vision, Distributed Systems, MQTT Messaging, Real-Time Control, WebSocket Communication

Made with Love by Joyeuse IRADUKUNDA
