"""
Persistent Search Tool - Never Give Up Object Search

This tool implements a multi-stage search strategy that systematically explores
the environment until the target object is found or all areas are exhausted.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_tool import BaseTool, ToolExecutionError
from .object_search_tool import ObjectSearchTool
from ...movement.controller import MovementController
from ...voice.tts import TextToSpeech
from ...vision.camera import Camera

logger = logging.getLogger(__name__)

class SearchStrategy(Enum):
    """Different search strategies in order of preference"""
    CURRENT_LOCATION = "current_location"
    NEARBY_SWEEP = "nearby_sweep"
    ROOM_BY_ROOM = "room_by_room"
    SYSTEMATIC_EXPLORATION = "systematic_exploration"
    EXHAUSTIVE_SEARCH = "exhaustive_search"

@dataclass
class SearchResult:
    """Result of a search operation"""
    found: bool
    confidence: float
    location: Optional[str]
    strategy_used: SearchStrategy
    time_taken: float
    areas_searched: List[str]

class PersistentSearchTool(BaseTool):
    """
    Advanced search tool that never gives up and systematically explores
    the environment using multiple search strategies.
    """
    
    name = "persistent_search"
    description = "Systematically search for objects using multiple strategies until found"
    parameters = {
        "object_name": {
            "type": str,
            "description": "Name of the object to search for",
            "required": True
        },
        "max_total_time": {
            "type": int,
            "description": "Maximum total search time in seconds",
            "required": False,
            "default": 300  # 5 minutes default
        },
        "announce_progress": {
            "type": bool,
            "description": "Whether to announce search progress",
            "required": False,
            "default": True
        }
    }
    
    def __init__(self):
        """Initialize the persistent search tool"""
        self.base_search_tool = ObjectSearchTool()
        self.movement = MovementController()
        self.tts = TextToSpeech()
        self.camera = Camera()
        
        # Search configuration
        self.search_strategies = [
            (SearchStrategy.CURRENT_LOCATION, 30),    # Quick local search
            (SearchStrategy.NEARBY_SWEEP, 45),        # Look around immediate area
            (SearchStrategy.ROOM_BY_ROOM, 60),        # Systematic room exploration
            (SearchStrategy.SYSTEMATIC_EXPLORATION, 90), # Full area coverage
            (SearchStrategy.EXHAUSTIVE_SEARCH, 120)   # Leave no stone unturned
        ]
        
        # Track searched areas to avoid repetition
        self.searched_areas = set()
        self.search_history = []
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute persistent search with multiple strategies
        
        Args:
            object_name: Object to search for
            max_total_time: Maximum search time in seconds
            announce_progress: Whether to announce progress
            
        Returns:
            Search result with detailed information
        """
        self.validate_parameters(**kwargs)
        
        object_name = kwargs.get("object_name")
        max_total_time = kwargs.get("max_total_time", 300)
        announce_progress = kwargs.get("announce_progress", True)
        
        logger.info(f"🔍 Starting persistent search for: {object_name}")
        
        if announce_progress:
            await self.tts.speak(f"I'll search thoroughly for the {object_name}. Let me check systematically.")
        
        search_start = time.time()
        total_areas_searched = []
        
        # Execute search strategies in order
        for strategy, strategy_timeout in self.search_strategies:
            # Check if we've exceeded total time
            elapsed = time.time() - search_start
            if elapsed >= max_total_time:
                logger.warning(f"⏰ Max search time ({max_total_time}s) reached")
                break
                
            # Calculate remaining time for this strategy
            remaining_time = min(strategy_timeout, max_total_time - elapsed)
            if remaining_time < 10:  # Not enough time for meaningful search
                break
            
            logger.info(f"🎯 Executing strategy: {strategy.value} (max {remaining_time}s)")
            
            if announce_progress:
                await self._announce_strategy(strategy, object_name)
            
            # Execute the strategy
            strategy_result = await self._execute_strategy(
                strategy, object_name, remaining_time
            )
            
            total_areas_searched.extend(strategy_result.areas_searched)
            
            # If found, return success
            if strategy_result.found:
                total_time = time.time() - search_start
                
                if announce_progress:
                    await self.tts.speak(f"Found the {object_name}! It was {strategy_result.location}.")
                
                return {
                    "success": True,
                    "found": True,
                    "object_name": object_name,
                    "location": strategy_result.location,
                    "confidence": strategy_result.confidence,
                    "strategy_used": strategy.value,
                    "total_time": total_time,
                    "areas_searched": total_areas_searched,
                    "search_complete": True
                }
            
            # Brief pause between strategies
            await asyncio.sleep(2)
        
        # If we get here, object was not found after all strategies
        total_time = time.time() - search_start
        
        if announce_progress:
            await self.tts.speak(
                f"I've searched thoroughly for the {object_name} in {len(total_areas_searched)} areas, "
                f"but haven't found it yet. It might be in a location I can't reach or see clearly."
            )
        
        return {
            "success": True,
            "found": False,
            "object_name": object_name,
            "location": None,
            "confidence": 0.0,
            "strategy_used": "all_strategies_exhausted",
            "total_time": total_time,
            "areas_searched": total_areas_searched,
            "search_complete": True,
            "recommendation": "The object might be in a drawer, cabinet, or area I cannot access."
        }
    
    async def _execute_strategy(self, strategy: SearchStrategy, object_name: str, 
                               max_time: float) -> SearchResult:
        """Execute a specific search strategy"""
        
        start_time = time.time()
        areas_searched = []
        
        try:
            if strategy == SearchStrategy.CURRENT_LOCATION:
                return await self._search_current_location(object_name, max_time)
                
            elif strategy == SearchStrategy.NEARBY_SWEEP:
                return await self._search_nearby_sweep(object_name, max_time)
                
            elif strategy == SearchStrategy.ROOM_BY_ROOM:
                return await self._search_room_by_room(object_name, max_time)
                
            elif strategy == SearchStrategy.SYSTEMATIC_EXPLORATION:
                return await self._search_systematic_exploration(object_name, max_time)
                
            elif strategy == SearchStrategy.EXHAUSTIVE_SEARCH:
                return await self._search_exhaustive(object_name, max_time)
                
        except Exception as e:
            logger.error(f"❌ Strategy {strategy.value} failed: {e}")
            
        # Fallback result if strategy fails
        return SearchResult(
            found=False,
            confidence=0.0,
            location=None,
            strategy_used=strategy,
            time_taken=time.time() - start_time,
            areas_searched=areas_searched
        )
    
    async def _search_current_location(self, object_name: str, max_time: float) -> SearchResult:
        """Search thoroughly in current location"""
        logger.info("🔍 Searching current location thoroughly")
        
        start_time = time.time()
        
        # Use the base search tool with higher confidence threshold
        result = await self.base_search_tool.execute(
            object_name=object_name,
            timeout=int(max_time),
            confidence_threshold=0.3  # Lower threshold for thorough search
        )
        
        return SearchResult(
            found=result.get("found", False),
            confidence=result.get("confidence", 0.0),
            location="current location" if result.get("found") else None,
            strategy_used=SearchStrategy.CURRENT_LOCATION,
            time_taken=time.time() - start_time,
            areas_searched=["current_position"]
        )
    
    async def _search_nearby_sweep(self, object_name: str, max_time: float) -> SearchResult:
        """Search by rotating and looking around nearby area"""
        logger.info("🔄 Performing nearby sweep search")
        
        start_time = time.time()
        areas_searched = []
        
        # Rotate and search in 8 directions
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        
        for angle in angles:
            if time.time() - start_time >= max_time:
                break
                
            # Turn to face this direction
            await self.movement.turn(angle=45, speed=30)  # Slow, careful turns
            areas_searched.append(f"direction_{angle}")
            
            # Quick search in this direction
            result = await self.base_search_tool.execute(
                object_name=object_name,
                timeout=5,  # Quick look
                confidence_threshold=0.4
            )
            
            if result.get("found"):
                return SearchResult(
                    found=True,
                    confidence=result.get("confidence", 0.0),
                    location=f"direction {angle} degrees",
                    strategy_used=SearchStrategy.NEARBY_SWEEP,
                    time_taken=time.time() - start_time,
                    areas_searched=areas_searched
                )
        
        return SearchResult(
            found=False,
            confidence=0.0,
            location=None,
            strategy_used=SearchStrategy.NEARBY_SWEEP,
            time_taken=time.time() - start_time,
            areas_searched=areas_searched
        )
    
    async def _search_room_by_room(self, object_name: str, max_time: float) -> SearchResult:
        """Search by moving to different areas of the room"""
        logger.info("🏠 Performing room-by-room search")
        
        start_time = time.time()
        areas_searched = []
        
        # Define search positions within the room
        search_positions = [
            ("center", 0, 0),
            ("corner_1", 1, 1),
            ("corner_2", -1, 1), 
            ("corner_3", -1, -1),
            ("corner_4", 1, -1),
            ("side_1", 0, 1),
            ("side_2", 1, 0),
            ("side_3", 0, -1),
            ("side_4", -1, 0)
        ]
        
        for position_name, x_offset, y_offset in search_positions:
            if time.time() - start_time >= max_time:
                break
                
            # Move to search position
            if x_offset != 0 or y_offset != 0:
                if x_offset != 0:
                    await self.movement.move_forward(distance=abs(x_offset), speed=40)
                if y_offset != 0:
                    await self.movement.turn(angle=90 if y_offset > 0 else -90, speed=30)
                    await self.movement.move_forward(distance=abs(y_offset), speed=40)
            
            areas_searched.append(position_name)
            
            # Search from this position
            result = await self.base_search_tool.execute(
                object_name=object_name,
                timeout=8,
                confidence_threshold=0.3
            )
            
            if result.get("found"):
                return SearchResult(
                    found=True,
                    confidence=result.get("confidence", 0.0),
                    location=f"room position: {position_name}",
                    strategy_used=SearchStrategy.ROOM_BY_ROOM,
                    time_taken=time.time() - start_time,
                    areas_searched=areas_searched
                )
        
        return SearchResult(
            found=False,
            confidence=0.0,
            location=None,
            strategy_used=SearchStrategy.ROOM_BY_ROOM,
            time_taken=time.time() - start_time,
            areas_searched=areas_searched
        )
    
    async def _search_systematic_exploration(self, object_name: str, max_time: float) -> SearchResult:
        """Systematic exploration of accessible areas"""
        logger.info("🗺️ Performing systematic exploration")
        
        start_time = time.time()
        areas_searched = []
        
        # Explore in a systematic pattern
        exploration_pattern = [
            ("forward_explore", "move_forward", 2),
            ("left_explore", "turn_left_explore", 90),
            ("right_explore", "turn_right_explore", 180),
            ("back_explore", "move_backward", 1),
        ]
        
        for area_name, movement_type, param in exploration_pattern:
            if time.time() - start_time >= max_time:
                break
                
            # Execute movement
            if movement_type == "move_forward":
                await self.movement.move_forward(distance=param, speed=35)
            elif movement_type == "turn_left_explore":
                await self.movement.turn(angle=-param, speed=30)
                await self.movement.move_forward(distance=1, speed=35)
            elif movement_type == "turn_right_explore":
                await self.movement.turn(angle=param, speed=30)
                await self.movement.move_forward(distance=1, speed=35)
            elif movement_type == "move_backward":
                await self.movement.move_forward(distance=-param, speed=35)
            
            areas_searched.append(area_name)
            
            # Search from this new position
            result = await self.base_search_tool.execute(
                object_name=object_name,
                timeout=10,
                confidence_threshold=0.25
            )
            
            if result.get("found"):
                return SearchResult(
                    found=True,
                    confidence=result.get("confidence", 0.0),
                    location=f"exploration area: {area_name}",
                    strategy_used=SearchStrategy.SYSTEMATIC_EXPLORATION,
                    time_taken=time.time() - start_time,
                    areas_searched=areas_searched
                )
        
        return SearchResult(
            found=False,
            confidence=0.0,
            location=None,
            strategy_used=SearchStrategy.SYSTEMATIC_EXPLORATION,
            time_taken=time.time() - start_time,
            areas_searched=areas_searched
        )
    
    async def _search_exhaustive(self, object_name: str, max_time: float) -> SearchResult:
        """Final exhaustive search with maximum effort"""
        logger.info("🔎 Performing exhaustive search - maximum effort")
        
        start_time = time.time()
        areas_searched = ["exhaustive_scan"]
        
        # Final comprehensive search with very low confidence threshold
        result = await self.base_search_tool.execute(
            object_name=object_name,
            timeout=int(max_time),
            confidence_threshold=0.15  # Very low threshold
        )
        
        return SearchResult(
            found=result.get("found", False),
            confidence=result.get("confidence", 0.0),
            location="exhaustive search result" if result.get("found") else None,
            strategy_used=SearchStrategy.EXHAUSTIVE_SEARCH,
            time_taken=time.time() - start_time,
            areas_searched=areas_searched
        )
    
    async def _announce_strategy(self, strategy: SearchStrategy, object_name: str):
        """Announce which search strategy is being used"""
        
        announcements = {
            SearchStrategy.CURRENT_LOCATION: f"Let me look carefully around here for the {object_name}...",
            SearchStrategy.NEARBY_SWEEP: f"Not here. Let me look around the surrounding area...",
            SearchStrategy.ROOM_BY_ROOM: f"Let me search different parts of this room for the {object_name}...",
            SearchStrategy.SYSTEMATIC_EXPLORATION: f"I'll explore other accessible areas to find the {object_name}...",
            SearchStrategy.EXHAUSTIVE_SEARCH: f"Doing a final thorough search for the {object_name}..."
        }
        
        message = announcements.get(strategy, f"Continuing search for {object_name}...")
        await self.tts.speak(message)