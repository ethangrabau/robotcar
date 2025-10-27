#!/usr/bin/env python3
"""
Test script for the hardware primitives.

This script tests the basic functionality of the PicarxController and Camera classes.
It performs a series of simple movements and captures an image to verify that
the hardware interfaces are working correctly.
"""

import sys
import time
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.movement.hardware_interface import PicarxController
from src.vision.camera import Camera

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_movement(controller):
    """Test basic movement functions of the PicarxController."""
    logger.info("Testing movement primitives...")
    
    # Test forward movement
    logger.info("Moving forward for 1 second...")
    controller.move_forward(50)
    time.sleep(1)
    controller.stop()
    time.sleep(0.5)
    
    # Test backward movement
    logger.info("Moving backward for 1 second...")
    controller.move_backward(50)
    time.sleep(1)
    controller.stop()
    time.sleep(0.5)
    
    # Test turning
    logger.info("Turning left...")
    controller.turn(-30)
    time.sleep(1)
    
    logger.info("Turning right...")
    controller.turn(30)
    time.sleep(1)
    
    logger.info("Resetting direction...")
    controller.turn(0)
    time.sleep(0.5)
    
    # Test camera movement
    logger.info("Testing camera pan and tilt...")
    controller.set_camera_angle(pan=-45, tilt=0)
    time.sleep(1)
    controller.set_camera_angle(pan=45, tilt=0)
    time.sleep(1)
    controller.set_camera_angle(pan=0, tilt=-20)
    time.sleep(1)
    controller.set_camera_angle(pan=0, tilt=20)
    time.sleep(1)
    controller.set_camera_angle(pan=0, tilt=0)
    time.sleep(1)
    
    # Test distance sensor
    distance = controller.get_distance()
    logger.info(f"Ultrasonic sensor distance: {distance} cm")
    
    logger.info("Movement tests completed.")

def test_camera(camera):
    """Test the Camera class functionality."""
    logger.info("Testing camera primitives...")
    
    # Start the camera
    if not camera.start(vflip=False, hflip=False):
        logger.error("Failed to start camera")
        return False
    
    # Give the camera time to initialize
    time.sleep(2)
    
    # Capture and save an image
    logger.info("Capturing image...")
    test_dir = "test_images"
    os.makedirs(test_dir, exist_ok=True)
    
    image_path = camera.save_frame("test_capture", directory=test_dir)
    if image_path:
        logger.info(f"Image saved to {image_path}")
    else:
        logger.error("Failed to save image")
    
    # Release the camera
    camera.release()
    logger.info("Camera test completed.")
    
    return image_path is not None

def main():
    """Main function to run the tests."""
    logger.info("Starting hardware primitives test...")
    
    try:
        # Initialize the hardware controller
        controller = PicarxController()
        logger.info("PicarxController initialized")
        
        # Test movement functions
        test_movement(controller)
        
        # Initialize the camera
        camera = Camera()
        logger.info("Camera initialized")
        
        # Test camera functions
        camera_success = test_camera(camera)
        
        # Reset everything
        controller.reset()
        
        # Final status
        if camera_success:
            logger.info("All tests completed successfully!")
        else:
            logger.warning("Tests completed with some issues. Check the logs.")
            
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
