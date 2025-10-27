"""
Camera module for the robot using the Vilib library.
Handles camera initialization, frame capture, and cleanup.
"""
import os
import logging
import numpy as np
from typing import Optional, Tuple
import cv2

logger = logging.getLogger(__name__)

class Camera:
    """Camera class for capturing frames using the Vilib library."""
    
    def __init__(self, resolution: Tuple[int, int] = (640, 480), framerate: int = 30):
        """Initialize the camera.
        
        Args:
            resolution: Tuple of (width, height) for the camera resolution.
            framerate: Frames per second for the camera.
        """
        self.resolution = resolution
        self.framerate = framerate
        self.is_running = False
        self.Vilib = None
        
        # Import Vilib here to avoid import errors when testing on non-Pi systems
        try:
            from vilib import Vilib
            self.Vilib = Vilib
            self.available = True
            logger.info("Vilib imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import Vilib: {str(e)}")
            self.available = False
    
    def start(self, vflip: bool = False, hflip: bool = False, web_display: bool = False) -> bool:
        """Start the camera.
        
        Args:
            vflip: Flip the image vertically
            hflip: Flip the image horizontally
            web_display: Enable web display at http://<ip>:9000/mjpg
            
        Returns:
            bool: True if the camera started successfully, False otherwise.
        """
        if not self.available:
            logger.error("Cannot start camera: Vilib not available")
            return False
            
        try:
            # Start the camera with the specified settings
            self.Vilib.camera_start(vflip=vflip, hflip=hflip)
            
            # Enable display if requested
            if web_display:
                self.Vilib.display(local=False, web=True)
                logger.info("Web display enabled at http://<ip>:9000/mjpg")
            
            # Wait for camera to initialize
            import time
            time.sleep(1)
            
            self.is_running = True
            logger.info("Camera started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera: {str(e)}")
            self.is_running = False
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from the camera.
        
        Returns:
            Optional[np.ndarray]: The captured frame as a numpy array in BGR format,
            or None if capture failed.
        """
        if not self.is_running:
            if not self.start():
                return None
                
        try:
            # Vilib stores the latest frame in Vilib.img (numpy array)
            if hasattr(self.Vilib, 'img') and self.Vilib.img is not None:
                # Vilib uses BGR format by default (same as OpenCV)
                return self.Vilib.img.copy()
            return None
            
        except Exception as e:
            logger.error(f"Failed to capture frame: {str(e)}")
            return None
    
    def save_frame(self, filename: str, directory: str = ".") -> Optional[str]:
        """Save the current frame to a file.
        
        Args:
            filename: Name of the file to save (without extension).
            directory: Directory to save the file in.
            
        Returns:
            Optional[str]: Path to the saved image, or None if save failed.
        """
        frame = self.capture_frame()
        if frame is None:
            return None
            
        try:
            os.makedirs(directory, exist_ok=True)
            filepath = os.path.join(directory, f"{filename}.jpg")
            success = cv2.imwrite(filepath, frame)
            if success:
                logger.info(f"Frame saved to {filepath}")
                return filepath
            else:
                logger.error(f"Failed to save frame to {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving frame: {str(e)}")
            return None
    
    def release(self):
        """Release camera resources."""
        if self.is_running and self.available:
            try:
                self.Vilib.camera_close()
                self.is_running = False
                logger.info("Camera released")
            except Exception as e:
                logger.error(f"Error releasing camera: {str(e)}")
    
    def __del__(self):
        """Ensure camera is released when the object is destroyed."""
        self.release()

# Example usage
if __name__ == "__main__":
    import time
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create camera instance
    camera = Camera()
    
    try:
        # Start camera with web display enabled
        if not camera.start(vflip=False, hflip=False, web_display=True):
            print("Failed to start camera")
            exit(1)
        
        print("Camera started. Press 's' to save a frame or 'q' to quit.")
        
        # Main loop
        while True:
            frame = camera.capture_frame()
            if frame is not None:
                # Display the frame
                cv2.imshow('Camera Feed', frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):  # Save frame on 's' key
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    saved_path = camera.save_frame(f"capture_{timestamp}")
                    if saved_path:
                        print(f"Frame saved to {saved_path}")
                
                # Exit on 'q' key
                if key == ord('q'):
                    break
                    
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Camera test completed.")
