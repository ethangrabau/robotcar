#!/usr/bin/env python3
"""
Movement Tools for the Robot Car

This module implements tools for movement and exploration.
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.agent.tools.base_tool import BaseTool
from src.movement.hardware_interface import PicarxController
from src.agent.tools.vision_tools import AnalyzeSceneTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExploreTool(BaseTool):
    """
    A tool for exploring the environment by rotating and analyzing the scene.
    """
    
    def __init__(self):
        """Initialize the exploration tool."""
        super().__init__()
        self.hardware = PicarxController()
        self.analyze_scene_tool = AnalyzeSceneTool()
        
        # Define the required parameters
        self.required_params = {
            "target": "The object or feature to look for during exploration",
            "rotation_steps": "Number of rotation steps to complete a 360-degree turn (default: 8)",
            "rotation_speed": "Speed of rotation (default: 30)",
            "rotation_time": "Time in seconds for each rotation step (default: 1.0)"
        }
        
        # Define optional parameters
        self.optional_params = {
            "detailed_analysis": "Whether to perform a detailed analysis at each step (default: False)"
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate the parameters for the tool.
        
        Args:
            **kwargs: The parameters to validate
            
        Returns:
            True if the parameters are valid, False otherwise
        """
        # Check required parameters
        if "target" not in kwargs:
            logger.error("Missing required parameter: target")
            return False
        
        return True
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the exploration by rotating and analyzing the scene.
        
        Args:
            target: The object or feature to look for
            rotation_steps: Number of rotation steps (default: 8)
            rotation_speed: Speed of rotation (default: 30)
            rotation_time: Time in seconds for each rotation step (default: 1.0)
            detailed_analysis: Whether to perform detailed analysis (default: False)
            
        Returns:
            A dictionary containing the exploration results
        """
        # Validate parameters
        if not self.validate_parameters(**kwargs):
            return {"success": False, "error": "Invalid parameters"}
        
        # Extract parameters
        target = kwargs.get("target")
        rotation_steps = int(kwargs.get("rotation_steps", 8))
        rotation_speed = int(kwargs.get("rotation_speed", 30))
        rotation_time = float(kwargs.get("rotation_time", 1.0))
        detailed_analysis = kwargs.get("detailed_analysis", False)
        
        logger.info(f"Starting exploration for target: {target}")
        
        # Initialize results
        results = {
            "success": True,
            "target_found": False,
            "observations": [],
            "target_location": None
        }
        
        try:
            # Perform a 360-degree exploration
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
                    
                except Exception as e:
                    logger.error(f"Error analyzing scene: {str(e)}")
                    results["observations"].append({
                        "step": step + 1,
                        "angle": (step * 360) // rotation_steps,
                        "error": str(e)
                    })
                
                # If target not found and more steps remain, rotate to the next position
                if not results["target_found"] and step < rotation_steps - 1:
                    logger.info(f"Rotating {360 // rotation_steps} degrees")
                    self.hardware.turn(rotation_speed)
                    time.sleep(rotation_time)
                    self.hardware.stop()
                    time.sleep(0.5)  # Short pause between movements
            
            # If we've completed a full 360-degree rotation, return to the original position
            if not results["target_found"]:
                logger.info("Target not found during exploration")
            
            return results
            
        except Exception as e:
            error_msg = f"Error during exploration: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        finally:
            # Ensure the robot stops after exploration
            self.hardware.stop()
