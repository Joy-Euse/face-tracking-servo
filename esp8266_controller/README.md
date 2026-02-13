# ESP8266 Edge Controller for Face Tracking Servo System

This ESP8266 controller subscribes to MQTT movement commands and controls a servo motor for face tracking applications.

## Hardware Requirements

### Components
- **ESP8266 Development Board**: NodeMCU, Wemos D1 Mini, or similar
- **Servo Motor**: SG90 or similar (9g micro servo recommended)
- **Power Supply**: 5V external power supply (recommended for servo)
- **Jumper Wires**: For connections
- **Breadboard**: For prototyping (optional)

### Wiring Diagram

```
ESP8266          Servo Motor
-------          ----------
D1 (GPIO5) <---- Signal (Orange/Yellow)
3.3V/5V    <---- VCC (Red)  [Use external 5V for better performance]
GND        <---- GND (Brown/Black)
```

**Important Notes:**
- For best performance, power the servo from an external 5V power supply
- Connect all grounds together (ESP8266, servo, power supply)
- The servo signal wire connects to D1 (GPIO5) on the ESP8266

## Software Setup

### 1. Arduino IDE Configuration
1. Install Arduino IDE (1.8.19 or newer)
2. Add ESP8266 board support:
   - File → Preferences → Additional Board Manager URLs
   - Add: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`
3. Tools → Board → Boards Manager → Search "esp8266" → Install
4. Select your board: Tools → Board → ESP8266 Boards → NodeMCU 1.0

### 2. Required Libraries
Install these libraries through the Arduino Library Manager:
- **PubSubClient** by Nick O'Leary (for MQTT)
- **ArduinoJson** by Benoit Blanchon (for JSON parsing)
- **Servo** (built-in)

### 3. Configuration
1. Copy `config.h.example` to `config.h`
2. Edit `config.h` with your settings:
   ```cpp
   #define WIFI_SSID "YourWiFiNetwork"
   #define WIFI_PASSWORD "YourWiFiPassword"
   #define MQTT_BROKER "192.168.1.100"  // Your MQTT broker IP
   #define TEAM_ID "Joyeuse01"          // Must match other components
   ```

### 4. Upload
1. Connect ESP8266 to your computer
2. Select the correct COM port in Arduino IDE
3. Upload the sketch

## MQTT Topics

The ESP8266 subscribes to the following topics:

### Movement Commands (Subscribe)
- **Topic**: `vision/<TEAM_ID>/movement`
- **Payload Format**:
  ```json
  {
    "status": "MOVE_LEFT|MOVE_RIGHT|CENTERED|NO_FACE",
    "confidence": 0.87,
    "timestamp": 1730000000
  }
  ```

### Heartbeat (Publish)
- **Topic**: `vision/<TEAM_ID>/heartbeat`
- **Payload Format**:
  ```json
  {
    "node": "esp8266",
    "status": "ONLINE",
    "timestamp": 1730000000,
    "servo_angle": 90,
    "last_movement": "CENTERED",
    "wifi_rssi": -45,
    "free_heap": 45000
  }
  ```

## Servo Behavior

### Movement Logic
- **MOVE_LEFT**: Decrease servo angle by `SERVO_STEP_SIZE` degrees
- **MOVE_RIGHT**: Increase servo angle by `SERVO_STEP_SIZE` degrees
- **CENTERED**: Move to center position (`SERVO_CENTER`)
- **NO_FACE**: Hold current position

### Safety Limits
- Minimum angle: `SERVO_MIN_ANGLE` (default: 30°)
- Maximum angle: `SERVO_MAX_ANGLE` (default: 150°)
- Step size: `SERVO_STEP_SIZE` (default: 2°)

## Serial Commands

Connect to the ESP8266 via Serial Monitor (115200 baud) for debugging:

```
info        - Print system information
center      - Move servo to center position
move <dir>  - Move servo (MOVE_LEFT/MOVE_RIGHT/CENTERED/NO_FACE)
heartbeat   - Send heartbeat message
help        - Show available commands
```

## Troubleshooting

### WiFi Connection Issues
1. Check SSID and password in `config.h`
2. Ensure WiFi network is available
3. Check signal strength (should be > -70 dBm)

### MQTT Connection Issues
1. Verify MQTT broker IP address
2. Check if broker is running and accessible
3. Ensure firewall allows MQTT port 1883
4. Verify team ID matches other components

### Servo Issues
1. Check wiring connections
2. Ensure adequate power supply
3. Verify servo is not damaged
4. Check for mechanical obstructions

### Common Problems

**Problem**: Servo jittering or twitching
**Solution**: Use external power supply for servo, add capacitor (1000µF) across servo power lines

**Problem**: MQTT connection drops frequently
**Solution**: Check WiFi signal strength, increase MQTT keepalive interval

**Problem**: Servo doesn't move
**Solution**: Check servo pin assignment, verify servo functionality with simple test code

## Integration with System

### Phase 1: Open-Loop Actuation
- Camera remains fixed on PC
- Servo responds to face movement commands
- No feedback from camera position

### Phase 2: Closed-Loop Tracking
- Camera mounted on servo
- System creates true feedback loop
- Smooth tracking with minimal jitter

## Performance Optimization

### Network Optimization
- Use wired Ethernet for MQTT broker if possible
- Position ESP8266 close to WiFi access point
- Consider using MQTT QoS 1 for important messages

### Servo Optimization
- Use high-quality servo with metal gears
- Add mechanical dampening to reduce vibration
- Implement motion smoothing in software if needed

## Security Considerations

- Change default WiFi credentials
- Use MQTT authentication if broker supports it
- Consider MQTT over SSL for production deployments
- Keep firmware updated for security patches

## License

This project is part of the Distributed Vision-Control System assignment.
