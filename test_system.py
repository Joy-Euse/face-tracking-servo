#!/usr/bin/env python3
"""
System Testing Script for Face Tracking System
Tests Phase 1: Open-Loop Actuation
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config import config_manager, get_config, get_mqtt_topics
    import paho.mqtt.client as mqtt
    import requests
    import websocket
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

class SystemTester:
    """Tests the complete face tracking system"""
    
    def __init__(self):
        self.config = get_config()
        self.topics = get_mqtt_topics()
        self.test_results = []
        self.mqtt_client = None
        self.ws_client = None
        self.received_messages = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log a test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
    
    def test_configuration(self):
        """Test system configuration"""
        print("\n=== Testing Configuration ===")
        
        # Test configuration validation
        config_valid = config_manager.validate()
        self.log_test_result("Configuration Validation", config_valid,
                            "All settings are valid" if config_valid else "Invalid configuration found")
        
        # Test MQTT topic generation
        topics = get_mqtt_topics()
        expected_topics = ["movement", "heartbeat", "base"]
        topics_valid = all(key in topics for key in expected_topics)
        self.log_test_result("MQTT Topics Generation", topics_valid,
                            f"Topics: {topics}" if topics_valid else "Missing topics")
        
        # Test team ID format
        team_id_valid = self.config.team_id.replace("_", "").replace("-", "").isalnum()
        self.log_test_result("Team ID Format", team_id_valid,
                            f"Team ID: {self.config.team_id}" if team_id_valid else "Invalid team ID format")
    
    def test_mqtt_broker(self):
        """Test MQTT broker connectivity"""
        print("\n=== Testing MQTT Broker ===")
        
        try:
            # Create MQTT client
            self.mqtt_client = mqtt.Client()
            connected = False
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected
                if rc == 0:
                    connected = True
                    self.logger.info("Connected to MQTT broker")
                else:
                    self.logger.error(f"MQTT connection failed with code {rc}")
            
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            time.sleep(2)
            
            self.log_test_result("MQTT Broker Connection", connected,
                                f"Connected to {self.config.mqtt_broker}:{self.config.mqtt_port}")
            
            if connected:
                # Test topic subscription
                subscribed = False
                def on_message(client, userdata, msg):
                    nonlocal subscribed
                    subscribed = True
                    self.received_messages.append(msg.payload.decode())
                
                self.mqtt_client.on_message = on_message
                self.mqtt_client.subscribe(self.topics["movement"])
                
                # Test message publishing
                test_message = {
                    "status": "TEST",
                    "confidence": 1.0,
                    "timestamp": int(time.time())
                }
                
                self.mqtt_client.publish(self.topics["movement"], json.dumps(test_message))
                time.sleep(1)
                
                message_received = len(self.received_messages) > 0
                self.log_test_result("MQTT Message Publish/Receive", message_received,
                                    "Test message successfully published and received")
            
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        except Exception as e:
            self.log_test_result("MQTT Broker Connection", False, f"Error: {e}")
    
    def test_backend_service(self):
        """Test backend service"""
        print("\n=== Testing Backend Service ===")
        
        base_url = f"http://localhost:{self.config.websocket_port}"
        
        try:
            # Test basic endpoints
            response = requests.get(f"{base_url}/", timeout=5)
            self.log_test_result("Backend Root Endpoint", response.status_code == 200,
                                f"Status code: {response.status_code}")
            
            response = requests.get(f"{base_url}/status", timeout=5)
            self.log_test_result("Backend Status Endpoint", response.status_code == 200,
                                f"Status code: {response.status_code}")
            
            response = requests.get(f"{base_url}/health", timeout=5)
            self.log_test_result("Backend Health Endpoint", response.status_code == 200,
                                f"Status code: {response.status_code}")
            
            # Test dashboard availability
            response = requests.get(f"{base_url}/dashboard", timeout=5)
            self.log_test_result("Dashboard Endpoint", response.status_code == 200,
                                f"Dashboard available at /dashboard")
            
        except requests.exceptions.ConnectionError:
            self.log_test_result("Backend Service Connection", False,
                                "Backend service not running or not accessible")
        except Exception as e:
            self.log_test_result("Backend Service Test", False, f"Error: {e}")
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        print("\n=== Testing WebSocket Connection ===")
        
        ws_url = f"ws://localhost:{self.config.websocket_port}/ws"
        ws_connected = False
        ws_messages = []
        
        try:
            def on_message(ws, message):
                ws_messages.append(message)
            
            def on_open(ws):
                nonlocal ws_connected
                ws_connected = True
                self.logger.info("WebSocket connection established")
            
            def on_error(ws, error):
                self.logger.error(f"WebSocket error: {error}")
            
            # Enable WebSocket tracing for debugging
            websocket.enableTrace(True)
            self.ws_client = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=self.ws_client.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection
            time.sleep(3)
            
            self.log_test_result("WebSocket Connection", ws_connected,
                                "Connected to WebSocket endpoint")
            
            if ws_connected:
                # Test ping/pong
                self.ws_client.send(json.dumps({"type": "ping"}))
                time.sleep(1)
                
                ping_response = any("pong" in msg for msg in ws_messages)
                self.log_test_result("WebSocket Ping/Pong", ping_response,
                                    "Ping/pong communication working")
            
            # Close WebSocket
            if self.ws_client:
                self.ws_client.close()
                
        except Exception as e:
            self.log_test_result("WebSocket Connection", False, f"Error: {e}")
    
    def test_vision_dependencies(self):
        """Test vision node dependencies"""
        print("\n=== Testing Vision Dependencies ===")
        
        try:
            # Test OpenCV
            import cv2
            cap = cv2.VideoCapture(self.config.camera_id)
            camera_available = cap.isOpened()
            self.log_test_result("Camera Access", camera_available,
                                f"Camera {self.config.camera_id} available" if camera_available else "Camera not accessible")
            
            if camera_available:
                ret, frame = cap.read()
                frame_valid = ret and frame is not None
                self.log_test_result("Frame Capture", frame_valid,
                                    f"Frame size: {frame.shape if frame_valid else 'N/A'}")
                cap.release()
            
            # Test MediaPipe
            import mediapipe as mp
            mp_face_detection = mp.solutions.face_detection
            self.log_test_result("MediaPipe Import", True, "MediaPipe successfully imported")
            
            # Test MQTT library
            import paho.mqtt.client as mqtt
            self.log_test_result("MQTT Library", True, "Paho MQTT client available")
            
        except ImportError as e:
            self.log_test_result("Vision Dependencies", False, f"Import error: {e}")
        except Exception as e:
            self.log_test_result("Vision Dependencies Test", False, f"Error: {e}")
    
    def test_phase1_functionality(self):
        """Test Phase 1: Open-Loop Actuation"""
        print("\n=== Testing Phase 1: Open-Loop Actuation ===")
        
        # This test requires the system to be running
        print("Note: This test requires vision node and ESP8266 to be running")
        print("Monitoring MQTT messages for 10 seconds...")
        
        try:
            # Connect to MQTT to monitor messages
            self.mqtt_client = mqtt.Client()
            movement_messages = []
            
            def on_message(client, userdata, msg):
                if "movement" in msg.topic:
                    try:
                        payload = json.loads(msg.payload.decode())
                        movement_messages.append(payload)
                        status = payload.get("status", "UNKNOWN")
                        confidence = payload.get("confidence", 0)
                        print(f"  Received: {status} (confidence: {confidence:.2f})")
                    except json.JSONDecodeError:
                        pass
            
            self.mqtt_client.on_message = on_message
            self.mqtt_client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
            self.mqtt_client.subscribe(self.topics["movement"])
            self.mqtt_client.loop_start()
            
            # Monitor for 10 seconds
            time.sleep(10)
            
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
            # Analyze results
            if movement_messages:
                statuses = [msg.get("status") for msg in movement_messages]
                unique_statuses = set(statuses)
                
                self.log_test_result("Movement Message Reception", True,
                                    f"Received {len(movement_messages)} messages")
                
                self.log_test_result("Movement Status Variety", len(unique_statuses) > 1,
                                    f"Statuses detected: {unique_statuses}")
                
                # Check confidence values
                confidences = [msg.get("confidence", 0) for msg in movement_messages]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                self.log_test_result("Confidence Values", avg_confidence > 0,
                                    f"Average confidence: {avg_confidence:.2f}")
            else:
                self.log_test_result("Movement Message Reception", False,
                                    "No movement messages received - is vision node running?")
            
        except Exception as e:
            self.log_test_result("Phase 1 Functionality Test", False, f"Error: {e}")
    
    def run_all_tests(self, skip_phase1=False):
        """Run all system tests"""
        print("🧪 Face Tracking System - Phase 1 Testing")
        print("=" * 50)
        
        # Run configuration tests first
        self.test_configuration()
        
        # Run dependency tests
        self.test_vision_dependencies()
        
        # Run backend tests
        self.test_backend_service()
        self.test_websocket_connection()
        
        # Run MQTT tests
        self.test_mqtt_broker()
        
        # Run Phase 1 functionality test
        if not skip_phase1:
            self.test_phase1_functionality()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}")
            if result["message"] and not result["passed"]:
                print(f"   {result['message']}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System is ready for Phase 1.")
        else:
            print("⚠️  Some tests failed. Please check the issues above.")
            
        print("\nNext steps:")
        if passed == total:
            print("1. Start backend: python start_backend.py")
            print("2. Start vision node: python start_vision.py")
            print("3. Upload ESP8266 code")
            print("4. Open dashboard: http://localhost:9002/dashboard")
        else:
            print("1. Fix failed tests")
            print("2. Re-run testing script")
            print("3. Proceed with deployment when all tests pass")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test Face Tracking System")
    parser.add_argument("--skip-phase1", action="store_true", 
                       help="Skip Phase 1 functionality test (requires running system)")
    parser.add_argument("--config", action="store_true",
                       help="Show configuration and exit")
    
    args = parser.parse_args()
    
    # Load environment variables
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    
    # Show configuration if requested
    if args.config:
        config_manager.print_config()
        return
    
    # Run tests
    tester = SystemTester()
    tester.run_all_tests(skip_phase1=args.skip_phase1)

if __name__ == "__main__":
    main()
