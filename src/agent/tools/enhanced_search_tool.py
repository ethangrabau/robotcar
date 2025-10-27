#!/usr/bin/env python3
"""
Enhanced Object Search Tool for PiCar-X
Implements advanced search patterns and obstacle avoidance
"""

import os
import sys
import time
import asyncio
import logging
import random
from typing import Dict, Any, Optional, List, Tuple

# Import base tool
from src.agent.tools.base_tool import BaseTool, ToolExecutionError

# Import memory components
from src.agent.memory.search_memory import SearchMemory, SearchArea

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_search.log')
    ]
)
logger = logging.getLogger(__name__)

class EnhancedSearchTool(BaseTool):
    """
    Enhanced tool for searching for objects with advanced patterns and obstacle avoidance
    """
    
    def __init__(self, car=None, vision_system=None, memory=None):
        """Initialize the search tool with hardware components"""
        super().__init__(
            name="search_for_object",
            description="Search for a specific object in the environment",
            parameters={
                "object_name": {
                    "type": "string",
                    "description": "Name of the object to search for"
                },
                "search_area": {
                    "type": "object",
                    "description": "Optional area to search within",
                    "required": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum time to search in seconds",
                    "default": 60,
                    "required": False
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence threshold for object detection",
                    "default": 0.7,
                    "required": False
                }
            }
        )
        
        # Store hardware components
        self.car = car
        self.vision_system = vision_system
        self.memory = memory or SearchMemory()
        
        # Search state
        self.is_searching = False
        self.current_search = None
        
        # Import hardware integration if not provided
        if self.car is None or self.vision_system is None:
            try:
                from src.agent.hardware_integration import get_hardware, get_vision_system, get_obstacle_avoidance
                self.car = self.car or get_hardware()
                self.vision_system = self.vision_system or get_vision_system()
                self.obstacle_avoidance = get_obstacle_avoidance()
                logger.info("Hardware components loaded from integration module")
            except ImportError as e:
                logger.error(f"Failed to import hardware integration: {e}")
                raise ToolExecutionError("Hardware integration not available")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the search for the specified object"""
        # Extract parameters
        object_name = kwargs.get("object_name")
        search_area = kwargs.get("search_area")
        timeout = kwargs.get("timeout", 60)
        min_confidence = kwargs.get("min_confidence", 0.7)
        
        if not object_name:
            raise ToolExecutionError("Object name is required")
        
        logger.info(f"Starting search for {object_name} with timeout {timeout}s")
        self.is_searching = True
        self.current_search = {
            "object_name": object_name,
            "start_time": time.time(),
            "timeout": timeout
        }
        
        try:
            # Check if we already know where this object is
            remembered_location = self.memory.recall_object_location(object_name)
            if remembered_location:
                logger.info(f"Found {object_name} in memory at {remembered_location}")
                return {
                    "status": "success",
                    "object_name": object_name,
                    "location": remembered_location,
                    "confidence": 0.9,  # High confidence since we remember it
                    "source": "memory"
                }
            
            # Start the search
            return await self._search_for_object(
                object_name=object_name,
                search_area=search_area,
                timeout=timeout,
                min_confidence=min_confidence
            )
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
        
        finally:
            self.is_searching = False
            self.current_search = None
    
    async def _search_for_object(self, object_name, search_area=None, timeout=60, min_confidence=0.7):
        """
        Implement the search logic with advanced patterns and obstacle avoidance
        """
        start_time = time.time()
        search_patterns = self._get_search_patterns()
        pattern_index = 0
        
        # Track visited positions to avoid revisiting
        visited_positions = set()
        
        while time.time() - start_time < timeout:
            # Check if we've exhausted our patterns
            if pattern_index >= len(search_patterns):
                pattern_index = 0  # Start over with the patterns
            
            # Get the current pattern
            current_pattern = search_patterns[pattern_index]
            logger.info(f"Executing search pattern {pattern_index + 1}/{len(search_patterns)}")
            
            # Execute each step in the pattern
            for step_idx, (action, value) in enumerate(current_pattern):
                # Check timeout
                if time.time() - start_time >= timeout:
                    logger.warning(f"Search timed out after {timeout}s")
                    return {
                        "status": "timeout",
                        "message": f"Search timed out after {timeout}s"
                    }
                
                # Execute the action
                try:
                    if action == "move":
                        # Check for obstacles before moving
                        path_clear = await self._check_and_avoid_obstacles()
                        if not path_clear:
                            logger.warning("Could not clear path, trying different direction")
                            continue
                        
                        await self.car.move_forward(value)
                    elif action == "turn":
                        await self.car.turn(value)
                    elif action == "scan":
                        # Scan for the object
                        result = await self._scan_for_object(object_name, min_confidence)
                        if result:
                            return result
                    
                    # Record the current position
                    current_pos = self.car.get_position()
                    pos_key = (round(current_pos[0], 1), round(current_pos[1], 1))
                    
                    # If we've been here before, try a different pattern
                    if pos_key in visited_positions:
                        logger.info(f"Already visited position {pos_key}, trying different pattern")
                        break
                    
                    visited_positions.add(pos_key)
                    self.memory.record_visit(current_pos)
                    
                except Exception as e:
                    logger.error(f"Error during search step {step_idx}: {e}")
            
            # Move to the next pattern
            pattern_index += 1
        
        # If we get here, we didn't find the object
        logger.warning(f"Failed to find {object_name} after {timeout}s")
        return {
            "status": "not_found",
            "message": f"Failed to find {object_name} after {timeout}s"
        }
    
    async def _scan_for_object(self, object_name, min_confidence):
        """Scan the current area for the target object"""
        logger.info(f"Scanning for {object_name}")
        
        # Capture image and detect objects
        detected_objects = await self.vision_system.detect_objects()
        
        # Check if we found the target object
        for obj in detected_objects:
            if obj['name'].lower() == object_name.lower() and obj.get('confidence', 0) >= min_confidence:
                # Record the sighting
                self.memory.record_sighting(
                    object_name=obj['name'],
                    position=obj['position'],
                    confidence=obj['confidence']
                )
                
                logger.info(f"Found {object_name} at {obj['position']} with {obj['confidence']:.1%} confidence")
                return {
                    "status": "success",
                    "object_name": object_name,
                    "location": obj['position'],
                    "confidence": obj['confidence'],
                    "source": "vision"
                }
        
        return None
    
    async def _check_and_avoid_obstacles(self):
        """Check for obstacles and avoid them if necessary"""
        if not hasattr(self, 'obstacle_avoidance'):
            # No obstacle avoidance available
            return True
            
        # Check if path is clear
        path_clear = await self.obstacle_avoidance.check_path()
        if not path_clear:
            # Try to avoid the obstacle
            return await self.obstacle_avoidance.avoid_obstacle()
        
        return True
    
    def _get_search_patterns(self):
        """
        Get a list of search patterns to try
        Each pattern is a list of (action, value) tuples
        Actions: "move" (distance in meters), "turn" (degrees), "scan" (None)
        """
        return [
            # Spiral pattern
            [
                ("scan", None),
                ("move", 0.5), ("turn", 90), ("scan", None),
                ("move", 0.5), ("turn", 90), ("scan", None),
                ("move", 1.0), ("turn", 90), ("scan", None),
                ("move", 1.0), ("turn", 90), ("scan", None),
                ("move", 1.5), ("turn", 90), ("scan", None),
            ],
            
            # Grid pattern
            [
                ("scan", None),
                ("move", 1.0), ("scan", None),
                ("turn", 90), ("move", 0.5), ("turn", 90), ("scan", None),
                ("move", 1.0), ("scan", None),
                ("turn", -90), ("move", 0.5), ("turn", -90), ("scan", None),
            ],
            
            # Random exploration
            [
                ("scan", None),
                ("turn", random.uniform(-45, 45)), ("move", random.uniform(0.5, 1.5)), ("scan", None),
                ("turn", random.uniform(-45, 45)), ("move", random.uniform(0.5, 1.5)), ("scan", None),
                ("turn", random.uniform(-45, 45)), ("move", random.uniform(0.5, 1.5)), ("scan", None),
            ]
        ]
