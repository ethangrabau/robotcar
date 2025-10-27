"""
Main entry point for the family robot assistant.
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent import RobotAgent
from src.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to initialize and run the robot agent."""
    logger.info("Starting Family Robot Assistant...")
    
    try:
        # Create and run the robot agent
        robot = RobotAgent(use_voice=True)
        robot.run_interactive()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\nA fatal error occurred: {e}")
        print("Check the logs for more details.")
    finally:
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
