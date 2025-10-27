#!/usr/bin/env python3
"""
Test script for the agent integration
Tests the object search functionality with proper hardware initialization
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Import the agent integration
try:
    from src.agent.integration import get_agent_system, run_search
    logger.info("Agent integration imported successfully")
except ImportError as e:
    logger.error(f"Failed to import agent integration: {e}")
    sys.exit(1)

async def test_search(object_name: str, timeout: int = 60):
    """Test the object search functionality"""
    logger.info(f"Testing search for: {object_name}")
    
    try:
        # Initialize the agent system
        agent = get_agent_system()
        if not agent.initialize():
            logger.error("Failed to initialize agent system")
            return
        
        # Run the search
        logger.info("Starting search...")
        result = await agent.search_for_object(object_name, timeout)
        
        # Log the result
        logger.info(f"Search result: {result}")
        return result
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        # Clean up
        if agent:
            agent.cleanup()

def main():
    """Main entry point"""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_agent.py <object_name> [timeout]")
        sys.exit(1)
    
    object_name = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    print(f"Testing search for '{object_name}' with timeout {timeout}s")
    
    try:
        # Run the test
        result = asyncio.run(test_search(object_name, timeout))
        
        # Print the result
        if result and result.get("status") == "success":
            print(f"✅ Object found: {result.get('location', 'unknown location')}")
        else:
            print(f"❌ Search failed: {result.get('message', 'unknown error')}")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
