#!/usr/bin/env python3
"""
Comprehensive integration test for PiCar-X agent system
Tests the hardware integration, enhanced search tool, and agent system
"""

import os
import sys
import time
import asyncio
import logging
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Import agent system
from src.agent.agent_system import get_agent_system, process_command

async def test_direct_tool_execution(object_name="ball", timeout=30):
    """Test direct tool execution"""
    logger.info(f"Testing direct tool execution for object: {object_name}")
    
    try:
        # Get the agent system
        agent = get_agent_system()
        
        # Execute the search tool directly
        logger.info(f"Executing search for {object_name}")
        result = await agent.search_for_object(
            object_name=object_name,
            timeout=timeout
        )
        
        # Log the result
        if result.get('status') == 'success':
            logger.info(f"✅ Found {object_name} at {result.get('location')} with {result.get('confidence'):.1%} confidence")
            print(f"✅ Found {object_name} at {result.get('location')} with {result.get('confidence'):.1%} confidence")
        else:
            logger.warning(f"❌ Failed to find {object_name}: {result.get('message')}")
            print(f"❌ Failed to find {object_name}: {result.get('message')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

async def test_natural_language_command(command="find the ball", timeout=30):
    """Test natural language command processing"""
    logger.info(f"Testing natural language command: '{command}'")
    
    try:
        # Process the command
        logger.info(f"Processing command: {command}")
        result = await process_command(command)
        
        # Log the result
        if result.get('status') == 'success':
            object_name = result.get('object_name', 'object')
            logger.info(f"✅ Command succeeded: Found {object_name} at {result.get('location')} with {result.get('confidence'):.1%} confidence")
            print(f"✅ Command succeeded: Found {object_name} at {result.get('location')} with {result.get('confidence'):.1%} confidence")
        else:
            logger.warning(f"❌ Command failed: {result.get('message')}")
            print(f"❌ Command failed: {result.get('message')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

async def run_tests(args):
    """Run all tests"""
    try:
        # Get the agent system
        agent = get_agent_system()
        
        # Run the tests
        if args.test_type == 'direct':
            await test_direct_tool_execution(args.object_name, args.timeout)
        elif args.test_type == 'command':
            await test_natural_language_command(args.command, args.timeout)
        else:
            # Run both tests
            print("=== Testing Direct Tool Execution ===")
            await test_direct_tool_execution(args.object_name, args.timeout)
            
            print("\n=== Testing Natural Language Command ===")
            command = args.command or f"find the {args.object_name}"
            await test_natural_language_command(command, args.timeout)
    
    finally:
        # Clean up
        if 'agent' in locals() and agent:
            agent.cleanup()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test the PiCar-X agent system')
    parser.add_argument('--object-name', type=str, default="ball", help='Object to search for')
    parser.add_argument('--timeout', type=int, default=30, help='Search timeout in seconds')
    parser.add_argument('--test-type', type=str, choices=['direct', 'command', 'both'], default='both',
                        help='Type of test to run')
    parser.add_argument('--command', type=str, help='Natural language command to process')
    
    args = parser.parse_args()
    
    print(f"Starting integration test with timeout {args.timeout}s")
    
    try:
        # Run the tests
        asyncio.run(run_tests(args))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
