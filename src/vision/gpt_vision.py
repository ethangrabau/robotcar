#!/usr/bin/env python3
"""
GPT-4 Vision integration for PiCar-X
Uses OpenAI's GPT-4 Vision API to detect objects in images
"""

import os
import sys
import time
import base64
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vision.log')
    ]
)
logger = logging.getLogger(__name__)

# Check for OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        from keys import OPENAI_API_KEY
    except ImportError:
        logger.warning("OpenAI API key not found in environment or keys.py")
        OPENAI_API_KEY = None

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
    logger.info("OpenAI package available")
except ImportError:
    logger.warning("OpenAI package not available, install with: pip install openai")
    OPENAI_AVAILABLE = False

# Try to import camera modules
CAMERA_AVAILABLE = False
try:
    import cv2
    CAMERA_AVAILABLE = True
    logger.info("OpenCV available for camera access")
except ImportError:
    logger.warning("OpenCV not available, install with: pip install opencv-python")

try:
    import vilib
    VILIB_AVAILABLE = True
    logger.info("vilib available for camera access")
except ImportError:
    logger.warning("vilib not available")
    VILIB_AVAILABLE = False

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
    logger.info("picamera2 available for camera access")
except ImportError:
    logger.warning("picamera2 not available")
    PICAMERA2_AVAILABLE = False

class GPTVision:
    """
    GPT-4 Vision integration for object detection
    """
    
    def __init__(self, api_key=None, model="gpt-4o"):
        """Initialize the GPT Vision integration"""
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.client = None
        self.camera = None
        self.camera_type = None
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize camera
        self._init_camera()
    
    def _init_camera(self):
        """Initialize the camera using available libraries"""
        if VILIB_AVAILABLE:
            try:
                vilib.init_camera()
                vilib.camera_start()
                self.camera_type = "vilib"
                logger.info("Camera initialized with vilib")
                return
            except Exception as e:
                logger.error(f"Failed to initialize camera with vilib: {e}")
        
        if PICAMERA2_AVAILABLE:
            try:
                self.camera = Picamera2()
                self.camera.start()
                self.camera_type = "picamera2"
                logger.info("Camera initialized with picamera2")
                return
            except Exception as e:
                logger.error(f"Failed to initialize camera with picamera2: {e}")
        
        if CAMERA_AVAILABLE:
            try:
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened():
                    raise Exception("Could not open camera")
                self.camera_type = "opencv"
                logger.info("Camera initialized with OpenCV")
                return
            except Exception as e:
                logger.error(f"Failed to initialize camera with OpenCV: {e}")
        
        logger.warning("No camera available, vision will be simulated")
    
    async def capture_image(self, save_path="current_view.jpg"):
        """Capture an image from the camera"""
        if not self.camera_type:
            logger.warning("No camera available, cannot capture image")
            return None
        
        try:
            if self.camera_type == "vilib":
                # Use vilib.img attribute instead of get_frame() method
                if hasattr(vilib, 'img') and vilib.img is not None:
                    cv2.imwrite(save_path, vilib.img)
                else:
                    logger.warning("No image available from vilib")
                    return None
            
            elif self.camera_type == "picamera2":
                self.camera.capture_file(save_path)
            
            elif self.camera_type == "opencv":
                ret, frame = self.camera.read()
                if ret:
                    cv2.imwrite(save_path, frame)
                else:
                    logger.warning("Failed to get frame from OpenCV camera")
                    return None
            
            logger.info(f"Image captured and saved to {save_path}")
            return save_path
        
        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            return None
    
    def _encode_image(self, image_path):
        """Encode image to base64 for API request"""
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None
        
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None
    
    async def detect_objects(self, image_path=None, prompt=None):
        """
        Detect objects in an image using GPT-4 Vision
        If image_path is None, capture a new image
        """
        # Capture image if not provided
        if image_path is None:
            image_path = await self.capture_image()
        
        if not image_path or not os.path.exists(image_path):
            logger.warning("No valid image available for object detection")
            return []
        
        # Check if OpenAI client is available
        if not self.client:
            logger.warning("OpenAI client not available, using mock detection")
            return [
                {"name": "ball", "confidence": 0.85, "position": (2, 1, 0)},
                {"name": "chair", "confidence": 0.75, "position": (3, 2, 0)}
            ]
        
        # Encode image
        base64_image = self._encode_image(image_path)
        if not base64_image:
            return []
        
        # Default prompt if not provided
        if not prompt:
            prompt = (
                "Identify all objects visible in this image. "
                "For each object, provide: "
                "1. The name of the object "
                "2. A confidence score between 0 and 1 "
                "3. The approximate position in the image (left/right/center, top/bottom/middle) "
                "Format your response as a JSON array of objects."
            )
        
        try:
            # Call GPT-4 Vision API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Extract response
            result = response.choices[0].message.content
            logger.info(f"GPT-4 Vision response: {result}")
            
            # Parse the response
            # Note: In a real implementation, you would parse the JSON response
            # For now, we'll return a simplified version
            return self._parse_vision_response(result)
        
        except Exception as e:
            logger.error(f"GPT-4 Vision API error: {e}")
            return []
    
    def _parse_vision_response(self, response_text):
        """Parse the GPT-4 Vision response text"""
        try:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                objects = json.loads(json_str)
                
                # Convert to our standard format
                result = []
                for obj in objects:
                    # Extract position information
                    pos_x, pos_y = 0, 0
                    if 'position' in obj:
                        pos_info = obj['position'].lower()
                        if 'left' in pos_info:
                            pos_x = -1
                        elif 'right' in pos_info:
                            pos_x = 1
                        
                        if 'top' in pos_info:
                            pos_y = -1
                        elif 'bottom' in pos_info:
                            pos_y = 1
                    
                    result.append({
                        'name': obj.get('name', 'unknown'),
                        'confidence': obj.get('confidence', 0.5),
                        'position': (pos_x, pos_y, 0)
                    })
                
                return result
            
            # If no JSON found, try to extract information from text
            objects = []
            lines = response_text.split('\n')
            current_object = {}
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Check for object name
                if ':' not in line and not current_object:
                    current_object = {'name': line.strip(), 'confidence': 0.7}
                
                # Check for confidence
                elif 'confidence' in line.lower():
                    try:
                        confidence = float(re.search(r'(\d+(\.\d+)?)', line).group(1))
                        if confidence > 1:
                            confidence /= 100  # Convert percentage to decimal
                        current_object['confidence'] = confidence
                    except:
                        pass
                
                # Check for position
                elif 'position' in line.lower():
                    pos_x, pos_y = 0, 0
                    if 'left' in line.lower():
                        pos_x = -1
                    elif 'right' in line.lower():
                        pos_x = 1
                    
                    if 'top' in line.lower():
                        pos_y = -1
                    elif 'bottom' in line.lower():
                        pos_y = 1
                    
                    current_object['position'] = (pos_x, pos_y, 0)
                
                # If we have a complete object, add it to the list
                if 'name' in current_object and 'confidence' in current_object:
                    if 'position' not in current_object:
                        current_object['position'] = (0, 0, 0)
                    
                    objects.append(current_object)
                    current_object = {}
            
            return objects
        
        except Exception as e:
            logger.error(f"Failed to parse vision response: {e}")
            return []
    
    def cleanup(self):
        """Clean up resources"""
        if self.camera_type == "vilib":
            try:
                vilib.camera_release()
                logger.info("vilib camera released")
            except:
                pass
        
        elif self.camera_type == "picamera2" and self.camera:
            try:
                self.camera.stop()
                logger.info("picamera2 stopped")
            except:
                pass
        
        elif self.camera_type == "opencv" and self.camera:
            try:
                self.camera.release()
                logger.info("OpenCV camera released")
            except:
                pass

# Singleton instance
_gpt_vision = None

def get_gpt_vision():
    """Get or create the GPT Vision singleton"""
    global _gpt_vision
    if _gpt_vision is None:
        _gpt_vision = GPTVision()
    return _gpt_vision
