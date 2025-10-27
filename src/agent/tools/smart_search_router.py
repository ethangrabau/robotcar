"""
Smart Search Router - Intelligent Search Planning

This tool learns from past searches and room discoveries to intelligently
route search requests to the most likely locations first.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

from .base_tool import BaseTool, ToolExecutionError
from .persistent_search_tool import PersistentSearchTool
from .room_discovery_tool import RoomDiscoveryTool, HouseMap
from ...voice.tts import TextToSpeech

logger = logging.getLogger(__name__)

@dataclass
class SearchPlan:
    """Plan for executing a smart search"""
    object_name: str
    predicted_rooms: List[Tuple[str, float]]  # (room_id, confidence)
    search_strategy: str
    estimated_duration: int
    fallback_plan: str

class SmartSearchRouter(BaseTool):
    """
    Intelligent search router that learns object-room associations
    and optimizes search strategies based on past experience.
    """
    
    name = "smart_search_router"
    description = "Intelligently route searches based on learned object-room patterns"
    parameters = {
        "object_name": {
            "type": str,
            "description": "Name of the object to search for",
            "required": True
        },
        "use_learning": {
            "type": bool,
            "description": "Whether to use learned patterns for search routing",
            "required": False,
            "default": True
        },
        "max_search_time": {
            "type": int,
            "description": "Maximum total search time in seconds",
            "required": False,
            "default": 300
        }
    }
    
    def __init__(self):
        """Initialize the smart search router"""
        self.persistent_search = PersistentSearchTool()
        self.room_discovery = RoomDiscoveryTool()
        self.house_map = self.room_discovery.house_map
        self.tts = TextToSpeech()
        
        # Common object-room associations for initial bootstrap
        self.default_associations = {
            "keys": ["kitchen", "bedroom", "living_room"],
            "remote": ["living_room", "bedroom"],
            "phone": ["kitchen", "bedroom", "living_room"],
            "wallet": ["bedroom", "kitchen"],
            "glasses": ["bedroom", "bathroom", "living_room"],
            "backpack": ["bedroom", "hallway"],
            "shoes": ["hallway", "bedroom"],
            "book": ["bedroom", "living_room", "office"],
            "charger": ["bedroom", "office", "kitchen"],
            "medicine": ["bathroom", "kitchen"],
            "toys": ["living_room", "bedroom"],
            "laptop": ["office", "bedroom", "living_room"],
            "headphones": ["bedroom", "office"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute smart search routing"""
        self.validate_parameters(**kwargs)
        
        object_name = kwargs.get("object_name")
        use_learning = kwargs.get("use_learning", True)
        max_search_time = kwargs.get("max_search_time", 300)
        
        logger.info(f"🧠 Planning smart search for: {object_name}")
        
        # Create search plan
        search_plan = await self._create_search_plan(object_name, use_learning)
        
        # Announce plan to user
        await self._announce_search_plan(search_plan)
        
        # Execute the planned search
        result = await self._execute_planned_search(search_plan, max_search_time)
        
        # Learn from the result
        await self._learn_from_search_result(object_name, result)
        
        return result
    
    async def _create_search_plan(self, object_name: str, use_learning: bool) -> SearchPlan:
        """Create an intelligent search plan"""
        
        predicted_rooms = []
        
        if use_learning:
            # Get learned associations from house map
            learned_locations = self.house_map.predict_object_locations(object_name)
            predicted_rooms.extend(learned_locations)
        
        # If no learned associations, use defaults
        if not predicted_rooms:
            default_room_types = self.default_associations.get(object_name.lower(), [])
            
            # Map default room types to actual discovered rooms
            for room_id, room_data in self.house_map.rooms.items():
                room_name = room_data.user_assigned_name or room_data.auto_detected_type
                if room_name.lower() in [rt.lower() for rt in default_room_types]:
                    confidence = 0.6  # Default confidence for type-based matching
                    predicted_rooms.append((room_id, confidence))
        
        # Sort by confidence
        predicted_rooms.sort(key=lambda x: x[1], reverse=True)
        
        # Determine search strategy
        if predicted_rooms:
            if predicted_rooms[0][1] > 0.7:
                strategy = "high_confidence_targeted"
            elif len(predicted_rooms) > 1:
                strategy = "multi_room_priority"
            else:
                strategy = "single_room_focused"
        else:
            strategy = "exploratory_search"
        
        # Estimate duration based on strategy and room count
        if strategy == "high_confidence_targeted":
            estimated_duration = 60
        elif strategy == "multi_room_priority":
            estimated_duration = 120 + (len(predicted_rooms) * 30)
        else:
            estimated_duration = 240
        
        return SearchPlan(
            object_name=object_name,
            predicted_rooms=predicted_rooms[:5],  # Top 5 predictions
            search_strategy=strategy,
            estimated_duration=min(estimated_duration, 300),
            fallback_plan="exhaustive_search"
        )
    
    async def _announce_search_plan(self, plan: SearchPlan):
        """Announce the search plan to the user"""
        
        if plan.search_strategy == "high_confidence_targeted":
            top_room = plan.predicted_rooms[0]
            room_name = self._get_room_name(top_room[0])
            await self.tts.speak(
                f"I have a strong feeling the {plan.object_name} is in the {room_name}. "
                f"Let me check there first!"
            )
        
        elif plan.search_strategy == "multi_room_priority":
            room_names = [self._get_room_name(room_id) for room_id, _ in plan.predicted_rooms[:3]]
            rooms_text = ", ".join(room_names[:-1]) + f", and {room_names[-1]}" if len(room_names) > 1 else room_names[0]
            await self.tts.speak(
                f"Based on what I've learned, the {plan.object_name} is most likely in the {rooms_text}. "
                f"I'll check these areas systematically."
            )
        
        elif plan.search_strategy == "single_room_focused":
            room_name = self._get_room_name(plan.predicted_rooms[0][0])
            await self.tts.speak(
                f"I'll focus my search for the {plan.object_name} in the {room_name} first, "
                f"then expand to other areas if needed."
            )
        
        else:  # exploratory_search
            await self.tts.speak(
                f"I haven't seen the {plan.object_name} before, so I'll search systematically "
                f"throughout the house and learn where it's kept for next time."
            )
    
    async def _execute_planned_search(self, plan: SearchPlan, max_search_time: int) -> Dict[str, Any]:
        """Execute the planned search strategy"""
        
        if plan.search_strategy in ["high_confidence_targeted", "multi_room_priority", "single_room_focused"]:
            # Room-by-room targeted search
            return await self._execute_targeted_search(plan, max_search_time)
        else:
            # Fall back to standard persistent search
            return await self.persistent_search.execute(
                object_name=plan.object_name,
                max_total_time=max_search_time,
                announce_progress=True
            )
    
    async def _execute_targeted_search(self, plan: SearchPlan, max_search_time: int) -> Dict[str, Any]:
        """Execute targeted search based on room predictions"""
        
        search_start_time = time.time()
        total_areas_searched = []
        
        # Search predicted rooms in order of confidence
        for room_id, confidence in plan.predicted_rooms:
            if time.time() - search_start_time >= max_search_time:
                break
                
            room_name = self._get_room_name(room_id)
            logger.info(f"🎯 Searching {room_name} (confidence: {confidence:.2f})")
            
            # Navigate to the room (simplified - would use actual navigation)
            await self.tts.speak(f"Checking the {room_name}...")
            
            # Search this specific room with focused time
            room_search_time = min(60, max_search_time - (time.time() - search_start_time))
            
            room_result = await self.persistent_search.execute(
                object_name=plan.object_name,
                max_total_time=int(room_search_time),
                announce_progress=False  # We're announcing at room level
            )
            
            total_areas_searched.extend(room_result.get("areas_searched", []))
            
            if room_result.get("found"):
                # Success! Learn this association
                self.house_map.learn_object_location(plan.object_name, room_id)
                
                await self.tts.speak(
                    f"Found the {plan.object_name} in the {room_name}! "
                    f"I'll remember it's often kept here."
                )
                
                return {
                    "success": True,
                    "found": True,
                    "object_name": plan.object_name,
                    "location": room_name,
                    "search_strategy": "smart_targeted",
                    "room_searched": room_name,
                    "confidence_was_correct": True,
                    "total_time": time.time() - search_start_time,
                    "areas_searched": total_areas_searched
                }
            
            await asyncio.sleep(2)  # Brief pause between rooms
        
        # If not found in predicted rooms, fall back to exhaustive search
        remaining_time = max_search_time - (time.time() - search_start_time)
        if remaining_time > 30:
            await self.tts.speak(
                f"Not in the expected locations. Let me search other areas..."
            )
            
            fallback_result = await self.persistent_search.execute(
                object_name=plan.object_name,
                max_total_time=int(remaining_time),
                announce_progress=True
            )
            
            # Merge results
            fallback_result["search_strategy"] = "smart_with_fallback"
            fallback_result["predicted_rooms_searched"] = len(plan.predicted_rooms)
            fallback_result["areas_searched"] = total_areas_searched + fallback_result.get("areas_searched", [])
            
            return fallback_result
        
        # Time exhausted
        return {
            "success": True,
            "found": False,
            "object_name": plan.object_name,
            "search_strategy": "smart_targeted_incomplete",
            "total_time": time.time() - search_start_time,
            "areas_searched": total_areas_searched,
            "message": f"Searched predicted locations but need more time to check other areas."
        }
    
    async def _learn_from_search_result(self, object_name: str, result: Dict[str, Any]):
        """Learn from search results to improve future searches"""
        
        if result.get("found"):
            # Positive learning - object was found
            location = result.get("location", "")
            room_searched = result.get("room_searched", "")
            
            if room_searched:
                # Find room ID from name
                room_id = self._find_room_id_by_name(room_searched)
                if room_id:
                    self.house_map.learn_object_location(object_name, room_id)
                    logger.info(f"📚 Learned: {object_name} found in {room_searched}")
        
        else:
            # Negative learning - update confidence for searched locations
            areas_searched = result.get("areas_searched", [])
            logger.info(f"📚 Noted: {object_name} not found in {len(areas_searched)} searched areas")
            
            # This could be used to reduce confidence scores for these locations
            # in future searches (not implemented in this version)
    
    def _get_room_name(self, room_id: str) -> str:
        """Get human-readable room name"""
        if room_id in self.house_map.rooms:
            room = self.house_map.rooms[room_id]
            return room.user_assigned_name or room.auto_detected_type
        return f"room {room_id}"
    
    def _find_room_id_by_name(self, room_name: str) -> Optional[str]:
        """Find room ID by name"""
        room_name_lower = room_name.lower()
        for room_id, room_data in self.house_map.rooms.items():
            assigned_name = room_data.user_assigned_name or ""
            detected_type = room_data.auto_detected_type or ""
            
            if (assigned_name.lower() == room_name_lower or 
                detected_type.lower() == room_name_lower):
                return room_id
        
        return None
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of what the system has learned"""
        
        learned_patterns = {}
        for obj, locations in self.house_map.object_locations.items():
            learned_patterns[obj] = [
                {
                    "room": self._get_room_name(loc.room_id),
                    "frequency": loc.frequency,
                    "confidence": loc.confidence,
                    "last_seen": loc.last_seen
                }
                for loc in sorted(locations, key=lambda x: x.confidence, reverse=True)
            ]
        
        return {
            "total_objects_learned": len(learned_patterns),
            "total_rooms_mapped": len(self.house_map.rooms),
            "object_patterns": learned_patterns,
            "room_summary": {
                room_id: {
                    "name": self._get_room_name(room_id),
                    "objects_found": [
                        obj for obj, locs in self.house_map.object_locations.items()
                        if any(loc.room_id == room_id for loc in locs)
                    ]
                }
                for room_id in self.house_map.rooms.keys()
            }
        }