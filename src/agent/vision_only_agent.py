#!/usr/bin/env python3
"""
Vision-Only Agent for the Robot Car

This script implements an enhanced agent that only uses vision capabilities,
without requiring hardware access. This allows testing the multi-step reasoning
while avoiding GPIO conflicts.

Phase 2 Implementation: Vision-only version for testing reasoning loop.
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
from src.vision.camera import Camera

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for cleanup
camera_instance = None
agent_instance = None

class VisionOnlyTool:
    """Base class for vision-only tools that simulate hardware actions."""
    
    def __init__(self):
        """Initialize the tool."""
        self.analyze_scene_tool = AnalyzeSceneTool()
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate the parameters for the tool.
        
        Args:
            **kwargs: The parameters to validate
            
        Returns:
            True if the parameters are valid, False otherwise
        """
        return True

class SimulatedExploreTool(VisionOnlyTool):
    """
    A simulated tool for exploring the environment using only vision.
    This version doesn't actually rotate the robot, but simulates the exploration
    by taking multiple pictures and analyzing them.
    """
    
    def __init__(self):
        """Initialize the simulated exploration tool."""
        super().__init__()
        
        # Define the required parameters
        self.required_params = {
            "target": "The object or feature to look for during exploration",
            "rotation_steps": "Number of rotation steps to complete a 360-degree turn (default: 3)",
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the simulated exploration by analyzing the scene multiple times.
        
        Args:
            target: The object or feature to look for
            rotation_steps: Number of simulated rotation steps (default: 3)
            
        Returns:
            A dictionary containing the exploration results
        """
        # Extract parameters
        target = kwargs.get("target")
        rotation_steps = int(kwargs.get("rotation_steps", 3))
        
        logger.info(f"Starting simulated exploration for target: {target}")
        
        # Initialize results
        results = {
            "success": True,
            "target_found": False,
            "observations": [],
            "target_location": None
        }
        
        try:
            # Perform a simulated exploration
            for step in range(rotation_steps):
                logger.info(f"Exploration step {step + 1}/{rotation_steps}")
                
                # Analyze the scene at the current position
                query = f"Do you see {target}? If yes, describe where it is located in the scene."
                
                try:
                    analysis_result = await self.analyze_scene_tool.execute(query=query)
                    analysis = analysis_result.get("analysis", "")
                    
                    # Add to observations
                    results["observations"].append({
                        "step": step + 1,
                        "angle": (step * 360) // rotation_steps,
                        "analysis": analysis
                    })
                    
                    # Check if target was found
                    if "yes" in analysis.lower() or "found" in analysis.lower() or "see" in analysis.lower() and target.lower() in analysis.lower():
                        results["target_found"] = True
                        results["target_location"] = {
                            "step": step + 1,
                            "angle": (step * 360) // rotation_steps,
                            "description": analysis
                        }
                        logger.info(f"Target found at step {step + 1}, angle {(step * 360) // rotation_steps} degrees")
                        break
                    
                    # Simulate rotation by waiting a moment
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error analyzing scene: {str(e)}")
                    results["observations"].append({
                        "step": step + 1,
                        "angle": (step * 360) // rotation_steps,
                        "error": str(e)
                    })
            
            # If we've completed all steps and didn't find the target
            if not results["target_found"]:
                logger.info("Target not found during simulated exploration")
            
            return results
            
        except Exception as e:
            error_msg = f"Error during simulated exploration: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

class VisionOnlyAgent:
    """
    An agent that uses only vision capabilities, avoiding hardware access.
    """
    
    def __init__(self):
        """Initialize the agent with vision-only tools."""
        global camera_instance
        
        # Initialize tools
        self.analyze_scene_tool = AnalyzeSceneTool()
        self.explore_tool = SimulatedExploreTool()
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
            explored = any(action.get("tool") == "SimulatedExploreTool" for action in history)
            
            if not explored:
                # If we haven't explored yet, add an exploration step
                self.state["plan"].append({
                    "tool": "SimulatedExploreTool",
                    "params": {
                        "target": goal,
                        "rotation_steps": 3
                    }
                })
                logger.info("Adding simulated exploration step to the plan")
            else:
                # If we've already explored, try analyzing the scene again
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
        elif tool == "SimulatedExploreTool":
            try:
                logger.info(f"Executing SimulatedExploreTool with params: {params}")
                result = await self.explore_tool.execute(**params)
                
                # Update state with the exploration result
                self.state["observations"].append({
                    "tool": "SimulatedExploreTool",
                    "params": params,
                    "result": result
                })
                
                # Format the result as a string for display
                if result.get("target_found", False):
                    location = result.get("target_location", {})
                    return f"Target found at angle {location.get('angle')} degrees! {location.get('description', '')}"
                else:
                    return f"Completed simulated exploration. Target not found."
            except Exception as e:
                error_msg = f"Error during simulated exploration: {str(e)}"
                logger.error(error_msg)
                
                # Update state with the error
                self.state["observations"].append({
                    "tool": "SimulatedExploreTool",
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

def signal_handler(sig, frame):
    """Handle signals like SIGINT (Ctrl+C) to clean up resources."""
    logger.info("Signal received, cleaning up resources...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Clean up all resources."""
    global agent_instance, camera_instance
    
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
    
    logger.info("Cleanup completed")

async def main():
    """Main function to run the vision-only agent."""
    global agent_instance
    
    logger.info("Starting the Vision-Only Agent...")
    
    # Initialize the agent
    agent_instance = VisionOnlyAgent()
    
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
