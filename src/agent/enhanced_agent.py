#!/usr/bin/env python3
"""
Enhanced Agent for the Robot Car

This script implements an enhanced agent with multi-step reasoning capabilities.
It maintains state between interactions and can create simple plans to achieve goals.

Phase 2 Implementation: Enhanced reasoning loop with state management and planning.
"""

import os
import sys
import logging
import asyncio
import signal
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.tools.vision_tools import AnalyzeSceneTool
from src.agent.tools.movement_tools import ExploreTool
from src.vision.camera import Camera
from src.movement.hardware_interface import PicarxController

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for cleanup
camera_instance = None
agent_instance = None
hardware_instance = None

class EnhancedAgent:
    """
    An enhanced agent that can maintain state and perform multi-step reasoning.
    """
    
    def __init__(self):
        """Initialize the agent with the necessary tools and state management."""
        global camera_instance, hardware_instance
        
        # Initialize hardware controller
        self.hardware = PicarxController()
        hardware_instance = self.hardware
        
        # Initialize tools
        self.analyze_scene_tool = AnalyzeSceneTool()
        self.explore_tool = ExploreTool()
        camera_instance = self.analyze_scene_tool.camera
        
        # Initialize agent state
        self.state = {
            "current_goal": None,
            "action_history": [],
            "observations": [],
            "plan": [],
            "current_plan_step": 0
        }
        
        # Check for OpenAI API key
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found in environment variables")
            logger.warning("Please set the OPENAI_API_KEY environment variable")
    
    async def analyze_scene(self, query: str) -> str:
        """
        Analyze the scene in front of the robot.
        
        Args:
            query: The question or instruction for analyzing the scene
            
        Returns:
            The analysis result
        """
        try:
            result = await self.analyze_scene_tool.execute(query=query)
            analysis = result["analysis"]
            
            # Update state with the observation
            self.state["observations"].append({
                "tool": "AnalyzeSceneTool",
                "query": query,
                "result": analysis
            })
            
            return analysis
        except Exception as e:
            error_msg = f"Error analyzing scene: {str(e)}"
            logger.error(error_msg)
            
            # Update state with the error
            self.state["observations"].append({
                "tool": "AnalyzeSceneTool",
                "query": query,
                "error": error_msg
            })
            
            return f"Error: {str(e)}"
    
    def set_goal(self, goal: str) -> None:
        """
        Set the current goal for the agent.
        
        Args:
            goal: The goal to achieve
        """
        self.state["current_goal"] = goal
        self.state["action_history"] = []
        self.state["observations"] = []
        self.state["plan"] = []
        self.state["current_plan_step"] = 0
        
        logger.info(f"New goal set: {goal}")
    
    async def think(self) -> Dict[str, Any]:
        """
        Generate the next action based on the current state.
        
        Returns:
            A dictionary containing the next action to take
        """
        # For now, we'll implement a simple reasoning loop
        # In a future iteration, this would call an LLM to generate a plan
        
        goal = self.state["current_goal"]
        history = self.state["action_history"]
        observations = self.state["observations"]
        
        # If we don't have a plan yet, create one
        if not self.state["plan"]:
            # Simple initial plan: analyze the scene for the goal
            self.state["plan"] = [
                {
                    "tool": "AnalyzeSceneTool",
                    "params": {"query": f"Do you see {goal}?"}
                }
            ]
            logger.info(f"Created initial plan: {self.state['plan']}")
        
        # If we've completed the plan but haven't achieved the goal, update the plan
        if self.state["current_plan_step"] >= len(self.state["plan"]):
            # Check if the goal was achieved based on the last observation
            if observations and "result" in observations[-1]:
                last_result = observations[-1]["result"].lower()
                if goal.lower() in last_result and ("found" in last_result or "see" in last_result):
                    return {"action": "complete", "message": f"Goal achieved: {goal}"}
            
            # Goal not achieved, need to create a new plan step
            # Check if we've already tried exploration
            explored = any(action.get("tool") == "ExploreTool" for action in history)
            
            if not explored:
                # If we haven't explored yet, add an exploration step
                self.state["plan"].append({
                    "tool": "ExploreTool",
                    "params": {
                        "target": goal,
                        "rotation_steps": 8,
                        "rotation_speed": 30,
                        "rotation_time": 1.0,
                        "detailed_analysis": True
                    }
                })
                logger.info("Adding exploration step to the plan")
            else:
                # If we've already explored, try analyzing the scene again
                # In a more sophisticated agent, we would use the exploration results
                # to decide where to look next
                self.state["plan"].append({
                    "tool": "AnalyzeSceneTool",
                    "params": {"query": f"Take another look. Do you see {goal}?"}
                })
                logger.info("Adding another analysis step to the plan")
            
            logger.info(f"Updated plan: {self.state['plan']}")
        
        # Get the next action from the plan
        next_action = self.state["plan"][self.state["current_plan_step"]]
        self.state["current_plan_step"] += 1
        
        # Add to action history
        self.state["action_history"].append(next_action)
        
        return next_action
    
    async def execute_action(self, action: Dict[str, Any]) -> str:
        """
        Execute the specified action.
        
        Args:
            action: The action to execute
            
        Returns:
            The result of the action
        """
        tool = action.get("tool")
        params = action.get("params", {})
        
        if tool == "AnalyzeSceneTool":
            return await self.analyze_scene(params.get("query", "What do you see?"))
        elif tool == "ExploreTool":
            try:
                logger.info(f"Executing ExploreTool with params: {params}")
                result = await self.explore_tool.execute(**params)
                
                # Update state with the exploration result
                self.state["observations"].append({
                    "tool": "ExploreTool",
                    "params": params,
                    "result": result
                })
                
                # Format the result as a string for display
                if result.get("target_found", False):
                    location = result.get("target_location", {})
                    return f"Target found at angle {location.get('angle')} degrees! {location.get('description', '')}"
                else:
                    return f"Completed 360-degree exploration. Target not found."
            except Exception as e:
                error_msg = f"Error during exploration: {str(e)}"
                logger.error(error_msg)
                
                # Update state with the error
                self.state["observations"].append({
                    "tool": "ExploreTool",
                    "params": params,
                    "error": error_msg
                })
                
                return f"Error: {error_msg}"
        else:
            error_msg = f"Unknown tool: {tool}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def cleanup(self):
        """Release resources when the agent is no longer needed."""
        if hasattr(self, 'analyze_scene_tool') and hasattr(self.analyze_scene_tool, 'camera'):
            try:
                logger.info("Cleaning up camera resources...")
                self.analyze_scene_tool.camera.release()
                logger.info("Camera resources released successfully")
            except Exception as e:
                logger.error(f"Error releasing camera resources: {str(e)}")
        
        if hasattr(self, 'hardware'):
            try:
                logger.info("Cleaning up hardware resources...")
                self.hardware.stop()
                logger.info("Hardware resources released successfully")
            except Exception as e:
                logger.error(f"Error releasing hardware resources: {str(e)}")

def signal_handler(sig, frame):
    """Handle signals like SIGINT (Ctrl+C) to clean up resources."""
    logger.info("Signal received, cleaning up resources...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Clean up all resources."""
    global agent_instance, camera_instance, hardware_instance
    
    if agent_instance:
        try:
            agent_instance.cleanup()
        except Exception as e:
            logger.error(f"Error during agent cleanup: {str(e)}")
    
    # Additional cleanup for camera if not handled by agent
    if camera_instance and hasattr(camera_instance, 'release'):
        try:
            camera_instance.release()
            logger.info("Camera released during cleanup")
        except Exception as e:
            logger.error(f"Error releasing camera: {str(e)}")
    
    # Additional cleanup for hardware if not handled by agent
    if hardware_instance and hasattr(hardware_instance, 'stop'):
        try:
            hardware_instance.stop()
            logger.info("Hardware stopped during cleanup")
        except Exception as e:
            logger.error(f"Error stopping hardware: {str(e)}")
    
    logger.info("Cleanup completed")

async def main():
    """Main function to run the enhanced agent."""
    global agent_instance
    
    logger.info("Starting the Enhanced Agent...")
    
    # Initialize the agent
    agent_instance = EnhancedAgent()
    
    try:
        while True:
            # Get user input for the goal
            print("\n" + "="*50)
            print("What is your goal? (Type 'exit' to quit)")
            goal = input("> ")
            
            # Check for exit command
            if goal.lower() in ["exit", "quit"]:
                break
            
            # Skip empty goals
            if not goal.strip():
                continue
            
            # Set the goal
            agent_instance.set_goal(goal)
            print(f"Goal set: {goal}")
            print("Starting reasoning loop...")
            
            # Enter the reasoning loop
            goal_achieved = False
            max_steps = 10  # Increase the number of steps for multi-step reasoning
            
            for step in range(max_steps):
                print(f"\nStep {step + 1}:")
                
                # Think about what to do next
                action = await agent_instance.think()
                
                # Check if the goal is complete
                if action.get("action") == "complete":
                    print(f"Goal achieved: {action.get('message')}")
                    goal_achieved = True
                    break
                
                # Execute the action
                print(f"Executing: {action}")
                result = await agent_instance.execute_action(action)
                
                # Display the result
                print("\nResult:")
                print("-"*50)
                print(result)
                print("-"*50)
            
            if not goal_achieved:
                print(f"Maximum steps reached. Goal not achieved: {goal}")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}", exc_info=True)
    finally:
        cleanup()
    
    logger.info("Agent stopped.")

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    finally:
        # Ensure cleanup happens even if asyncio.run fails
        cleanup()
