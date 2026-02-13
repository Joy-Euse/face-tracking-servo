/*
 * Configuration Header for ESP8266 Face Tracking Controller
 * Copy this file to config.h and modify the settings below
 */

#ifndef CONFIG_H
#define CONFIG_H

// ==================== WiFi Configuration ====================
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// ==================== MQTT Configuration ====================
#define MQTT_BROKER "YOUR_MQTT_BROKER_IP"  // e.g., "192.168.1.100"
#define MQTT_PORT 1883
#define TEAM_ID "Joyeuse01"  // Must match PC and backend team ID

// ==================== Hardware Configuration ====================
#define SERVO_PIN D1  // GPIO5 on NodeMCU
#define SERVO_MIN_PULSE 500   // 0.5ms pulse (0 degrees)
#define SERVO_MAX_PULSE 2400  // 2.4ms pulse (180 degrees)

// ==================== Servo Control Parameters ====================
#define SERVO_CENTER 90      // Center position (degrees)
#define SERVO_STEP_SIZE 2    // Degrees to move per command
#define SERVO_MIN_ANGLE 30   // Minimum angle (left limit)
#define SERVO_MAX_ANGLE 150  // Maximum angle (right limit)

// ==================== Timing Configuration ====================
#define HEARTBEAT_INTERVAL 30000  // 30 seconds in milliseconds
#define WIFI_RETRY_INTERVAL 5000  // 5 seconds in milliseconds
#define MQTT_RETRY_INTERVAL 5000   // 5 seconds in milliseconds

#endif // CONFIG_H
