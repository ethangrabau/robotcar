#!/usr/bin/env python3
"""
Main Agent Script for the Robot Car

This script implements a simple agent that can analyze the scene
in front of the robot using the AnalyzeSceneTool.

Phase 1 Implementation: Simple tool-based architecture with a single tool.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.tools.vision_tools import AnalyzeSceneTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleAgent:
    """
    A simple agent that can analyze the scene in front of the robot.
    """
    
    def __init__(self):
        """Initialize the agent with the necessary tools."""
        self.analyze_scene_tool = AnalyzeSceneTool()
        
        # Check for OpenAI API key
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found in environment variables")
            logger.warning("Please set the OPENAI_API_KEY environment variable")
    
    async def analyze_scene(self, query):
        """
        Analyze the scene in front of the robot.
        
        Args:
            query: The question or instruction for analyzing the scene
            
        Returns:
            The analysis result
        """
        try:
            result = await self.analyze_scene_tool.execute(query=query)
            return result["analysis"]
        except Exception as e:
            logger.error(f"Error analyzing scene: {str(e)}")
            return f"Error: {str(e)}"

async def main():
    """Main function to run the agent."""
    logger.info("Starting the Simple Agent...")
    
    # Initialize the agent
    agent = SimpleAgent()
    
    try:
        while True:
            # Get user input
            print("\n" + "="*50)
            print("What should I look for? (Type 'exit' to quit)")
            query = input("> ")
            
            # Check for exit command
            if query.lower() in ["exit", "quit"]:
                break
            
            # Skip empty queries
            if not query.strip():
                continue
            
            print(f"Analyzing scene for: {query}")
            
            # Analyze the scene
            result = await agent.analyze_scene(query)
            
            # Display the result
            print("\nAnalysis Result:")
            print("-"*50)
            print(result)
            print("-"*50)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}", exc_info=True)
    
    logger.info("Agent stopped.")

if __name__ == "__main__":
    asyncio.run(main())
