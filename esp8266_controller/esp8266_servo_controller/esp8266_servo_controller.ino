/*
 * ESP8266 Edge Controller for Face Tracking Servo System
 * Subscribes to MQTT movement commands and controls servo motor accordingly
 * 
 * Hardware Requirements:
 * - ESP8266 (NodeMCU or Wemos D1 Mini)
 * - SG90 or similar servo motor
 * - External power supply for servo (recommended)
 * 
 * Wiring:
 * - Servo VCC -> 5V external power (or ESP8266 5V pin if using small servo)
 * - Servo GND -> Common ground
 * - Servo Signal -> ESP8266 D1 (GPIO5)
 * 
 * MQTT Topics:
 * - vision/<team_id>/movement (subscribe)
 * - vision/<team_id>/heartbeat (optional publish)
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>
#include <ArduinoJson.h>

// ==================== CONFIGURATION ====================

// WiFi Configuration
const char* WIFI_SSID = "RCA_OUTDOOR_5GHZ";
const char* WIFI_PASSWORD = "RCA@2025";

// MQTT Configuration
const char* MQTT_BROKER = "127.0.0.1";  // e.g., "192.168.1.100"
const int MQTT_PORT = 1883;
const char* TEAM_ID = "Joyeuse01";  // Must match the team ID used by PC and backend

// MQTT Topics
char MOVEMENT_TOPIC[50];
char HEARTBEAT_TOPIC[50];

// Servo Configuration
const int SERVO_PIN = D1;  // GPIO5 on NodeMCU
const int SERVO_MIN_PULSE = 500;   // 0.5ms pulse (0 degrees)
const int SERVO_MAX_PULSE = 2400;  // 2.4ms pulse (180 degrees)

// Servo Control Parameters
const int SERVO_CENTER = 90;      // Center position (degrees)
const int SERVO_STEP_SIZE = 2;     // Degrees to move per command
const int SERVO_MIN_ANGLE = 30;   // Minimum angle (left limit)
const int SERVO_MAX_ANGLE = 150;   // Maximum angle (right limit)

// Timing Configuration
const unsigned long HEARTBEAT_INTERVAL = 30000;  // 30 seconds
const unsigned long WIFI_RETRY_INTERVAL = 5000;  // 5 seconds
const unsigned long MQTT_RETRY_INTERVAL = 5000;   // 5 seconds

// ==================== GLOBAL VARIABLES ====================

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Servo trackingServo;

// State variables
int currentServoAngle = SERVO_CENTER;
String lastMovementStatus = "UNKNOWN";
unsigned long lastHeartbeatTime = 0;
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;

// Status flags
bool wifiConnected = false;
bool mqttConnected = false;
bool servoInitialized = false;

// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=== ESP8266 Face Tracking Servo Controller ===");
  Serial.println("Team ID: " + String(TEAM_ID));
  
  // Generate MQTT topics
  sprintf(MOVEMENT_TOPIC, "vision/%s/movement", TEAM_ID);
  sprintf(HEARTBEAT_TOPIC, "vision/%s/heartbeat", TEAM_ID);
  
  Serial.print("Movement Topic: ");
  Serial.println(MOVEMENT_TOPIC);
  Serial.print("Heartbeat Topic: ");
  Serial.println(HEARTBEAT_TOPIC);
  
  // Initialize servo
  initializeServo();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Initialize MQTT
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  
  Serial.println("Setup completed. Starting main loop...");
}

// ==================== MAIN LOOP ====================

void loop() {
  unsigned long currentTime = millis();
  
  // Handle WiFi connection
  if (!wifiConnected) {
    if (currentTime - lastWifiAttempt >= WIFI_RETRY_INTERVAL) {
      connectToWiFi();
      lastWifiAttempt = currentTime;
    }
    return; // Skip other operations until WiFi is connected
  }
  
  // Handle MQTT connection
  if (!mqttConnected) {
    if (currentTime - lastMqttAttempt >= MQTT_RETRY_INTERVAL) {
      connectToMqtt();
      lastMqttAttempt = currentTime;
    }
    return; // Skip other operations until MQTT is connected
  }
  
  // Process MQTT messages
  if (!mqttClient.loop()) {
    mqttConnected = false;
    Serial.println("MQTT connection lost");
    return;
  }
  
  // Send heartbeat
  if (currentTime - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
    sendHeartbeat();
    lastHeartbeatTime = currentTime;
  }
  
  // Small delay to prevent overwhelming the system
  delay(10);
}

// ==================== SERVO CONTROL ====================

void initializeServo() {
  Serial.println("Initializing servo...");
  
  // Attach servo
  trackingServo.attach(SERVO_PIN, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  
  // Move to center position
  trackingServo.write(currentServoAngle);
  
  // Wait for servo to reach position
  delay(500);
  
  servoInitialized = true;
  Serial.println("Servo initialized at position: " + String(currentServoAngle) + " degrees");
}

void moveServo(String movement) {
  if (!servoInitialized) {
    Serial.println("Servo not initialized, ignoring movement command");
    return;
  }
  
  int newAngle = currentServoAngle;
  
  // Determine new angle based on movement command
  if (movement == "MOVE_LEFT") {
    newAngle = currentServoAngle - SERVO_STEP_SIZE;
    Serial.println("Moving LEFT");
  } else if (movement == "MOVE_RIGHT") {
    newAngle = currentServoAngle + SERVO_STEP_SIZE;
    Serial.println("Moving RIGHT");
  } else if (movement == "CENTERED") {
    newAngle = SERVO_CENTER;
    Serial.println("Moving to CENTER");
  } else if (movement == "NO_FACE") {
    // Keep current position when no face detected
    Serial.println("No face detected - holding position");
    return;
  } else {
    Serial.println("Unknown movement command: " + movement);
    return;
  }
  
  // Constrain angle to valid range
  newAngle = constrain(newAngle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
  
  // Only move if angle actually changed
  if (newAngle != currentServoAngle) {
    currentServoAngle = newAngle;
    trackingServo.write(currentServoAngle);
    
    Serial.print("Servo moved to: ");
    Serial.print(currentServoAngle);
    Serial.println(" degrees");
    
    // Visual feedback on built-in LED
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
    digitalWrite(LED_BUILTIN, HIGH);
  } else {
    Serial.println("Servo already at target position");
  }
  
  lastMovementStatus = movement;
}

// ==================== WiFi FUNCTIONS ====================

void connectToWiFi() {
  Serial.println("Connecting to WiFi...");
  Serial.print("SSID: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  // Wait for connection (with timeout)
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.println("WiFi connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    wifiConnected = false;
    Serial.println();
    Serial.println("WiFi connection failed");
  }
}

// ==================== MQTT FUNCTIONS ====================

void connectToMqtt() {
  if (!wifiConnected) {
    Serial.println("Cannot connect to MQTT: WiFi not connected");
    return;
  }
  
  Serial.println("Connecting to MQTT broker...");
  Serial.print("Broker: ");
  Serial.print(MQTT_BROKER);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  
  // Generate client ID with team ID and chip ID
  String clientId = "esp8266_" + String(TEAM_ID) + "_" + String(ESP.getChipId());
  
  if (mqttClient.connect(clientId.c_str())) {
    mqttConnected = true;
    Serial.println("MQTT connected successfully!");
    
    // Subscribe to movement topic
    if (mqttClient.subscribe(MOVEMENT_TOPIC)) {
      Serial.print("Subscribed to: ");
      Serial.println(MOVEMENT_TOPIC);
    } else {
      Serial.println("Failed to subscribe to movement topic");
    }
    
    // Send initial heartbeat
    sendHeartbeat();
    
  } else {
    mqttConnected = false;
    Serial.print("MQTT connection failed, rc=");
    Serial.println(mqttClient.state());
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("MQTT message received [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);
  
  // Parse JSON message
  DynamicJsonDocument doc(256);
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Extract movement status
  String status = doc["status"] | "UNKNOWN";
  float confidence = doc["confidence"] | 0.0;
  unsigned long timestamp = doc["timestamp"] | 0;
  
  Serial.print("Movement status: ");
  Serial.print(status);
  Serial.print(" (confidence: ");
  Serial.print(confidence, 2);
  Serial.print(", timestamp: ");
  Serial.print(timestamp);
  Serial.println(")");
  
  // Move servo based on movement command
  moveServo(status);
}

void sendHeartbeat() {
  if (!mqttConnected) {
    return;
  }
  
  // Create heartbeat message
  DynamicJsonDocument doc(256);
  doc["node"] = "esp8266";
  doc["status"] = "ONLINE";
  doc["timestamp"] = millis() / 1000;  // Unix timestamp approximation
  doc["servo_angle"] = currentServoAngle;
  doc["last_movement"] = lastMovementStatus;
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  
  String message;
  serializeJson(doc, message);
  
  // Publish heartbeat
  if (mqttClient.publish(HEARTBEAT_TOPIC, message.c_str())) {
    Serial.print("Heartbeat published: ");
    Serial.println(message);
  } else {
    Serial.println("Failed to publish heartbeat");
  }
}

// ==================== UTILITY FUNCTIONS ====================

void printSystemInfo() {
  Serial.println("=== System Information ===");
  Serial.print("Chip ID: ");
  Serial.println(ESP.getChipId());
  Serial.print("Flash Size: ");
  Serial.print(ESP.getFlashChipSize());
  Serial.println(" bytes");
  Serial.print("Free Heap: ");
  Serial.print(ESP.getFreeHeap());
  Serial.println(" bytes");
  Serial.print("CPU Frequency: ");
  Serial.print(ESP.getCpuFreqMHz());
  Serial.println(" MHz");
  Serial.print("WiFi Status: ");
  Serial.println(wifiConnected ? "Connected" : "Disconnected");
  Serial.print("MQTT Status: ");
  Serial.println(mqttConnected ? "Connected" : "Disconnected");
  Serial.print("Current Servo Angle: ");
  Serial.print(currentServoAngle);
  Serial.println(" degrees");
  Serial.println("========================");
}

// ==================== SERIAL COMMANDS ====================

void processSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "info") {
      printSystemInfo();
    } else if (command == "center") {
      moveServo("CENTERED");
    } else if (command.startsWith("move ")) {
      String direction = command.substring(5);
      moveServo(direction);
    } else if (command == "heartbeat") {
      sendHeartbeat();
    } else if (command == "help") {
      Serial.println("Available commands:");
      Serial.println("  info     - Print system information");
      Serial.println("  center   - Move servo to center position");
      Serial.println("  move <direction> - Move servo (MOVE_LEFT/MOVE_RIGHT/CENTERED/NO_FACE)");
      Serial.println("  heartbeat - Send heartbeat message");
      Serial.println("  help     - Show this help message");
    } else {
      Serial.println("Unknown command. Type 'help' for available commands.");
    }
  }
}
