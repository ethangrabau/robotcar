#!/usr/bin/env python3
"""
Test script for the Google TV integration
This script allows testing voice commands for controlling Google TV from the robot
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the media command handler
from src.agent.media_command_handler import MediaCommandHandler

async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test Google TV integration with voice commands')
    parser.add_argument('--command', type=str, help='Voice command to test (e.g., "play Paw Patrol on Disney")')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    args = parser.parse_args()
    
    print("=== Google TV Integration Test ===")
    print("This script tests voice commands for controlling Google TV")
    
    # Create the media command handler
    handler = MediaCommandHandler()
    
    try:
        if args.interactive:
            # Interactive mode
            print("\nEntering interactive mode. Type 'exit' to quit.")
            print("\nExample commands:")
            print("  - play Paw Patrol on Disney")
            print("  - play cat videos on YouTube")
            print("  - pause")
            print("  - resume")
            print("  - stop")
            
            while True:
                command = input("\nEnter a voice command: ")
                if command.lower() in ['exit', 'quit']:
                    break
                
                # Process the command
                is_media = await handler.is_media_command(command)
                if not is_media:
                    print("This doesn't appear to be a media-related command.")
                    continue
                
                print(f"Processing: '{command}'")
                result = await handler.process_command(command)
                
                print("\nResult:")
                print(f"  Success: {result['success']}")
                print(f"  Response: {result['response']}")
        
        elif args.command:
            # Single command mode
            command = args.command
            print(f"\nProcessing command: '{command}'")
            
            # Check if it's a media command
            is_media = await handler.is_media_command(command)
            if not is_media:
                print("This doesn't appear to be a media-related command.")
                return
            
            # Process the command
            result = await handler.process_command(command)
            
            print("\nResult:")
            print(f"  Success: {result['success']}")
            print(f"  Response: {result['response']}")
        
        else:
            # No arguments provided, show usage
            parser.print_help()
    
    finally:
        # Clean up
        handler.cleanup()
        print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(main())
