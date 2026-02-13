#!/usr/bin/env python3
"""
PC Vision Node for Distributed Face Tracking System
Captures camera frames, detects faces, and publishes movement commands via MQTT
"""

import json
import time
import logging
import argparse
from typing import Optional, Tuple
from dataclasses import dataclass

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import mediapipe as mp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TrackingConfig:
    """Configuration for the vision node"""
    team_id: str = "team01"
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    camera_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    detection_confidence: float = 0.5
    tracking_confidence: float = 0.5
    center_threshold: float = 0.15  # 15% of frame width from center
    publish_interval: float = 0.1  # 100ms between messages

class FaceTracker:
    """Face detection and tracking using MediaPipe"""
    
    def __init__(self, config: TrackingConfig):
        self.config = config
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize face detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=config.detection_confidence
        )
        
        # Camera setup
        self.cap = cv2.VideoCapture(config.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {config.camera_id}")
        
        self.last_publish_time = 0
        
    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[float, float, float]]:
        """
        Detect face in frame and return (center_x, center_y, confidence)
        Returns None if no face detected
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)
        
        if results.detections:
            detection = results.detections[0]  # Use the first detected face
            
            # Get bounding box
            bbox = detection.location_data.relative_bounding_box
            h, w, _ = frame.shape
            
            # Calculate center of face
            center_x = bbox.xmin + bbox.width / 2
            center_y = bbox.ymin + bbox.height / 2
            
            return center_x, center_y, detection.score[0]
        
        return None
    
    def determine_movement(self, face_center: Optional[Tuple[float, float, float]]) -> str:
        """
        Determine movement command based on face position
        Returns: MOVE_LEFT, MOVE_RIGHT, CENTERED, or NO_FACE
        """
        if face_center is None:
            return "NO_FACE"
        
        center_x, center_y, confidence = face_center
        
        # Check if face is centered (within threshold)
        if abs(center_x - 0.5) < self.config.center_threshold:
            return "CENTERED"
        elif center_x < 0.5:
            return "MOVE_LEFT"
        else:
            return "MOVE_RIGHT"
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get frame from camera"""
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to capture frame")
            return None
        return frame
    
    def release(self):
        """Release resources"""
        if hasattr(self, 'cap'):
            self.cap.release()
        cv2.destroyAllWindows()

class MQTTPublisher:
    """MQTT client for publishing movement commands"""
    
    def __init__(self, config: TrackingConfig):
        self.config = config
        self.client = mqtt.Client()
        self.movement_topic = f"vision/{config.team_id}/movement"
        self.heartbeat_topic = f"vision/{config.team_id}/heartbeat"
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # Connect to broker
        try:
            self.client.connect(config.mqtt_broker, config.mqtt_port, 60)
            self.client.loop_start()
            logger.info(f"Connected to MQTT broker at {config.mqtt_broker}:{config.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connection established")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"MQTT disconnected with code {rc}")
    
    def publish_movement(self, status: str, confidence: float = 0.0):
        """Publish movement status to MQTT"""
        message = {
            "status": status,
            "confidence": confidence,
            "timestamp": int(time.time())
        }
        
        try:
            self.client.publish(self.movement_topic, json.dumps(message))
            logger.debug(f"Published movement: {message}")
        except Exception as e:
            logger.error(f"Failed to publish movement: {e}")
    
    def publish_heartbeat(self):
        """Publish heartbeat message"""
        message = {
            "node": "pc",
            "status": "ONLINE",
            "timestamp": int(time.time())
        }
        
        try:
            self.client.publish(self.heartbeat_topic, json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish heartbeat: {e}")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()

class VisionNode:
    """Main vision node that combines face tracking and MQTT publishing"""
    
    def __init__(self, config: TrackingConfig):
        self.config = config
        self.tracker = FaceTracker(config)
        self.mqtt = MQTTPublisher(config)
        self.running = False
        self.last_heartbeat = 0
        
    def run(self):
        """Main loop for vision processing"""
        logger.info("Starting vision node...")
        self.running = True
        
        try:
            while self.running:
                frame = self.tracker.get_frame()
                if frame is None:
                    continue
                
                # Detect face
                face_data = self.tracker.detect_face(frame)
                
                # Determine movement
                movement = self.tracker.determine_movement(face_data)
                confidence = face_data[2] if face_data else 0.0
                
                # Publish movement at specified interval
                current_time = time.time()
                if current_time - self.tracker.last_publish_time >= self.config.publish_interval:
                    self.mqtt.publish_movement(movement, confidence)
                    self.tracker.last_publish_time = current_time
                
                # Publish heartbeat every 30 seconds
                if current_time - self.last_heartbeat >= 30:
                    self.mqtt.publish_heartbeat()
                    self.last_heartbeat = current_time
                
                # Display frame with visualization (optional)
                self._display_frame(frame, face_data, movement)
                
                # Check for exit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()
    
    def _display_frame(self, frame: np.ndarray, face_data: Optional[Tuple[float, float, float]], movement: str):
        """Display frame with face detection and movement status"""
        h, w, _ = frame.shape
        
        # Draw face bounding box if detected
        if face_data:
            center_x, center_y, confidence = face_data
            
            # Draw center point
            cv2.circle(frame, (int(center_x * w), int(center_y * h)), 5, (0, 255, 0), -1)
            
            # Draw center line
            cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 0), 2)
            
            # Draw threshold lines
            left_threshold = int((0.5 - self.config.center_threshold) * w)
            right_threshold = int((0.5 + self.config.center_threshold) * w)
            cv2.line(frame, (left_threshold, 0), (left_threshold, h), (0, 255, 255), 1)
            cv2.line(frame, (right_threshold, 0), (right_threshold, h), (0, 255, 255), 1)
        
        # Display movement status
        status_color = {
            "MOVE_LEFT": (0, 0, 255),
            "MOVE_RIGHT": (0, 0, 255),
            "CENTERED": (0, 255, 0),
            "NO_FACE": (128, 128, 128)
        }.get(movement, (255, 255, 255))
        
        cv2.putText(frame, f"Status: {movement}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"Team: {self.config.team_id}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Face Tracking - Vision Node", frame)
    
    def stop(self):
        """Stop the vision node"""
        logger.info("Stopping vision node...")
        self.running = False
        self.tracker.release()
        self.mqtt.disconnect()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Face Tracking Vision Node")
    parser.add_argument("--team-id", default="team01", help="Team identifier for MQTT topics")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--camera-id", type=int, default=0, help="Camera device ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration
    config = TrackingConfig(
        team_id=args.team_id,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        camera_id=args.camera_id
    )
    
    # Create and run vision node
    try:
        node = VisionNode(config)
        node.run()
    except Exception as e:
        logger.error(f"Failed to start vision node: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
