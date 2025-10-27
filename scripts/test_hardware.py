#!/usr/bin/env python3
"""
Comprehensive hardware test script for the robot.
Run this on the Raspberry Pi to test all hardware components.
"""
import time
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hardware_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_movements(robot):
    """Test basic robot movements."""
    tests = [
        ("Moving forward at 30% speed", lambda: robot.move_forward(30)),
        ("Moving backward at 30% speed", lambda: robot.move_backward(30)),
        ("Turning left 30 degrees", lambda: robot.turn_left(30)),
        ("Turning right 30 degrees", lambda: robot.turn_right(30)),
        ("Looking around", robot.look_around),
    ]
    
    for description, movement_func in tests:
        try:
            logger.info(f"Testing: {description}")
            print(f"\n--- {description} ---")
            print("Starting in 2 seconds... (Press Ctrl+C to skip)")
            time.sleep(2)
            
            movement_func()
            time.sleep(3)  # Let the movement happen for 3 seconds
            robot.stop()
            
            print("Test passed!")
            logger.info(f"Test passed: {description}")
            
        except KeyboardInterrupt:
            print("\nTest interrupted!")
            robot.stop()
            break
        except Exception as e:
            logger.error(f"Test failed: {description} - {str(e)}")
            print(f"Error: {str(e)}")
        
        time.sleep(1)  # Pause between tests

def test_camera():
    """Test the camera functionality."""
    try:
        import cv2
        from src.vision.camera import Camera
        
        logger.info("Testing camera...")
        print("\n--- Testing Camera ---")
        
        camera = Camera()
        print("Camera initialized. Capturing test image...")
        
        # Capture and save a test image
        frame = camera.capture_frame()
        if frame is not None:
            test_image_path = "camera_test.jpg"
            cv2.imwrite(test_image_path, frame)
            print(f"Test image saved to {test_image_path}")
            logger.info(f"Test image saved to {test_image_path}")
        else:
            print("Failed to capture image from camera")
            logger.error("Failed to capture image from camera")
            
        camera.release()
        
    except ImportError as e:
        logger.warning(f"Camera test skipped - missing dependency: {e}")
        print("Camera test skipped - missing dependencies")
    except Exception as e:
        logger.error(f"Camera test failed: {str(e)}")
        print(f"Camera test error: {str(e)}")

def test_audio():
    """Test the audio input/output."""
    try:
        from src.voice import TextToSpeech
        
        logger.info("Testing audio output...")
        print("\n--- Testing Audio Output ---")
        print("You should hear a test message...")
        
        tts = TextToSpeech()
        tts.speak("This is a test of the text-to-speech system. If you can hear this, the audio is working correctly.")
        
        print("Audio test complete!")
        logger.info("Audio output test passed")
        
    except Exception as e:
        logger.error(f"Audio test failed: {str(e)}")
        print(f"Audio test error: {str(e)}")

def main():
    """Run all hardware tests."""
    from src.movement.navigation import RobotController
    from src.utils.gpio_utils import setup_gpio, is_raspberry_pi
    
    print("\n=== Robot Hardware Test ===\n")
    
    if not is_raspberry_pi():
        print("Warning: Not running on a Raspberry Pi. Some tests may not work correctly.")
        logger.warning("Not running on a Raspberry Pi")
    
    # Initialize GPIO
    setup_gpio()
    
    try:
        # Initialize robot controller
        print("Initializing robot controller...")
        robot = RobotController()
        
        # Run tests
        test_movements(robot)
        test_camera()
        test_audio()
        
        print("\nAll tests completed!")
        logger.info("All hardware tests completed successfully")
        
    except Exception as e:
        logger.critical(f"Hardware test failed: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("Check the logs for more details.")
    finally:
        # Clean up
        if 'robot' in locals():
            robot.stop()
        print("\nHardware test complete.")

if __name__ == "__main__":
    main()
