#!/usr/bin/env python3
"""
Simple test script for the camera module.
Run this on the Raspberry Pi to test the camera.
"""
import cv2
import time
import logging
from pathlib import Path

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from vision.camera import Camera

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('camera_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_camera():
    """Test the camera functionality."""
    print("Testing camera...")
    camera = Camera()
    
    try:
        # Start the camera
        if not camera.start():
            print("❌ Failed to start camera")
            return False
        
        print("✅ Camera started successfully")
        print("Capturing test image in 2 seconds...")
        time.sleep(2)
        
        # Capture a frame
        frame = camera.capture_frame()
        if frame is None:
            print("❌ Failed to capture frame")
            return False
        
        print(f"✅ Captured frame with shape: {frame.shape}")
        
        # Save the frame
        image_path = camera.save_frame("camera_test")
        if image_path:
            print(f"✅ Test image saved to: {image_path}")
        else:
            print("❌ Failed to save test image")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Camera test failed: {str(e)}", exc_info=True)
        return False
    finally:
        camera.release()

def main():
    """Run all camera tests."""
    print("=== Camera Test ===\n")
    
    if not test_camera():
        print("\n❌ Camera test failed!")
        return 1
    
    print("\n✅ All camera tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
