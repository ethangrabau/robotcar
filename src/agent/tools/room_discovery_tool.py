"""
Room Discovery and Mapping Tool

This tool enables the robot to discover, classify, and map rooms in the house,
building a persistent understanding of the environment over time.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .base_tool import BaseTool, ToolExecutionError
from .vision_tools import AnalyzeSceneTool
from ...movement.controller import MovementController
from ...voice.tts import TextToSpeech

logger = logging.getLogger(__name__)

@dataclass
class RoomData:
    """Data structure for a discovered room"""
    room_id: str
    name: str
    auto_detected_type: str
    user_assigned_name: Optional[str]
    objects_present: List[str]
    description: str
    confidence: float
    discovery_timestamp: str
    last_visited: str
    visit_count: int
    connections: List[str]  # IDs of connected rooms
    estimated_size: str
    distinctive_features: List[str]

@dataclass
class ObjectLocation:
    """Track where objects are typically found"""
    object_name: str
    room_id: str
    frequency: int  # How many times found here
    last_seen: str
    confidence: float

class HouseMap:
    """Manages the overall house map and room relationships"""
    
    def __init__(self, map_file_path: str = "house_map.json"):
        self.map_file = Path(map_file_path)
        self.rooms: Dict[str, RoomData] = {}
        self.object_locations: Dict[str, List[ObjectLocation]] = {}
        self.current_room_id: Optional[str] = None
        self.exploration_history: List[str] = []
        
        # Load existing map if available
        self.load_map()
    
    def add_room(self, room_data: RoomData) -> str:
        """Add a new room to the map"""
        self.rooms[room_data.room_id] = room_data
        self.save_map()
        return room_data.room_id
    
    def update_room(self, room_id: str, updates: Dict[str, Any]):
        """Update room data"""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            for key, value in updates.items():
                if hasattr(room, key):
                    setattr(room, key, value)
            self.save_map()
    
    def find_room_by_features(self, objects: List[str], description: str) -> Optional[str]:
        """Find existing room by matching features"""
        for room_id, room in self.rooms.items():
            # Calculate similarity score
            common_objects = set(objects) & set(room.objects_present)
            object_similarity = len(common_objects) / max(len(objects), len(room.objects_present), 1)
            
            # Description similarity (simple keyword matching)
            desc_words = set(description.lower().split())
            room_desc_words = set(room.description.lower().split())
            desc_similarity = len(desc_words & room_desc_words) / max(len(desc_words), len(room_desc_words), 1)
            
            # If similarity is high enough, consider it the same room
            if object_similarity > 0.6 or desc_similarity > 0.7:
                return room_id
        
        return None
    
    def learn_object_location(self, object_name: str, room_id: str):
        """Learn that an object was found in a specific room"""
        if object_name not in self.object_locations:
            self.object_locations[object_name] = []
        
        # Find existing location record or create new one
        location_found = False
        for location in self.object_locations[object_name]:
            if location.room_id == room_id:
                location.frequency += 1
                location.last_seen = datetime.now().isoformat()
                location.confidence = min(1.0, location.frequency * 0.2)  # Cap at 1.0
                location_found = True
                break
        
        if not location_found:
            new_location = ObjectLocation(
                object_name=object_name,
                room_id=room_id,
                frequency=1,
                last_seen=datetime.now().isoformat(),
                confidence=0.2
            )
            self.object_locations[object_name].append(new_location)
        
        self.save_map()
    
    def predict_object_locations(self, object_name: str) -> List[Tuple[str, float]]:
        """Predict which rooms an object is likely to be in"""
        if object_name not in self.object_locations:
            return []
        
        # Sort by confidence (frequency-based)
        locations = self.object_locations[object_name]
        sorted_locations = sorted(locations, key=lambda x: x.confidence, reverse=True)
        
        return [(loc.room_id, loc.confidence) for loc in sorted_locations]
    
    def get_room_summary(self) -> Dict[str, Any]:
        """Get a summary of discovered rooms"""
        return {
            "total_rooms": len(self.rooms),
            "rooms": {
                room_id: {
                    "name": room.user_assigned_name or room.auto_detected_type,
                    "type": room.auto_detected_type,
                    "objects": room.objects_present,
                    "last_visited": room.last_visited,
                    "visit_count": room.visit_count
                }
                for room_id, room in self.rooms.items()
            },
            "object_patterns": {
                obj: [(loc.room_id, loc.confidence) for loc in locations]
                for obj, locations in self.object_locations.items()
            }
        }
    
    def save_map(self):
        """Save map to persistent storage"""
        try:
            map_data = {
                "rooms": {room_id: asdict(room) for room_id, room in self.rooms.items()},
                "object_locations": {
                    obj: [asdict(loc) for loc in locations]
                    for obj, locations in self.object_locations.items()
                },
                "current_room_id": self.current_room_id,
                "exploration_history": self.exploration_history,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.map_file, 'w') as f:
                json.dump(map_data, f, indent=2)
                
            logger.info(f"💾 Map saved to {self.map_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save map: {e}")
    
    def load_map(self):
        """Load map from persistent storage"""
        try:
            if not self.map_file.exists():
                logger.info("📍 No existing map found, starting fresh")
                return
            
            with open(self.map_file, 'r') as f:
                map_data = json.load(f)
            
            # Reconstruct rooms
            self.rooms = {
                room_id: RoomData(**room_data)
                for room_id, room_data in map_data.get("rooms", {}).items()
            }
            
            # Reconstruct object locations
            self.object_locations = {
                obj: [ObjectLocation(**loc_data) for loc_data in loc_list]
                for obj, loc_list in map_data.get("object_locations", {}).items()
            }
            
            self.current_room_id = map_data.get("current_room_id")
            self.exploration_history = map_data.get("exploration_history", [])
            
            logger.info(f"🗺️ Loaded map with {len(self.rooms)} rooms")
            
        except Exception as e:
            logger.error(f"❌ Failed to load map: {e}")
            # Start with empty map if loading fails
            self.rooms = {}
            self.object_locations = {}

class RoomDiscoveryTool(BaseTool):
    """
    Tool for discovering and mapping rooms in the house
    """
    
    name = "room_discovery"
    description = "Discover, classify, and map rooms in the house"
    parameters = {
        "action": {
            "type": str,
            "description": "Action to perform: 'analyze_current', 'explore_new', 'show_map', 'name_room'",
            "required": True
        },
        "room_name": {
            "type": str,
            "description": "Custom name for a room (used with 'name_room' action)",
            "required": False
        },
        "room_id": {
            "type": str,
            "description": "Room ID to rename (used with 'name_room' action)",
            "required": False
        }
    }
    
    def __init__(self):
        """Initialize the room discovery tool"""
        self.vision_tool = AnalyzeSceneTool()
        self.movement = MovementController()
        self.tts = TextToSpeech()
        self.house_map = HouseMap()
        
        # Room classification patterns
        self.room_patterns = {
            "kitchen": {
                "keywords": ["stove", "refrigerator", "fridge", "sink", "microwave", "oven", "counter", "cabinet"],
                "priority": 0.9
            },
            "bedroom": {
                "keywords": ["bed", "dresser", "nightstand", "closet", "pillow", "blanket"],
                "priority": 0.8
            },
            "living_room": {
                "keywords": ["couch", "sofa", "tv", "television", "coffee table", "chair", "remote"],
                "priority": 0.8
            },
            "bathroom": {
                "keywords": ["toilet", "shower", "bathtub", "sink", "mirror", "towel"],
                "priority": 0.9
            },
            "dining_room": {
                "keywords": ["dining table", "chairs", "chandelier", "plates"],
                "priority": 0.7
            },
            "office": {
                "keywords": ["desk", "computer", "chair", "bookshelf", "monitor"],
                "priority": 0.7
            },
            "hallway": {
                "keywords": ["narrow", "corridor", "doors", "passage"],
                "priority": 0.5
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute room discovery action"""
        self.validate_parameters(**kwargs)
        
        action = kwargs.get("action")
        
        if action == "analyze_current":
            return await self._analyze_current_room()
        elif action == "explore_new":
            return await self._explore_new_areas()
        elif action == "show_map":
            return await self._show_house_map()
        elif action == "name_room":
            room_name = kwargs.get("room_name")
            room_id = kwargs.get("room_id")
            return await self._name_room(room_id, room_name)
        else:
            raise ToolExecutionError(f"Unknown action: {action}")
    
    async def _analyze_current_room(self) -> Dict[str, Any]:
        """Analyze and classify the current room"""
        logger.info("🏠 Analyzing current room")
        
        # Capture detailed room analysis
        room_analysis = await self.vision_tool.execute(
            query="""Analyze this room in detail. Describe:
            1. What type of room this appears to be
            2. All furniture and objects you can see
            3. The general size and layout
            4. Any distinctive features or decorations
            5. Colors and lighting
            Be very thorough and specific.""",
            save_image=True,
            image_dir="room_mapping"
        )
        
        analysis_text = room_analysis.get("analysis", "")
        
        # Extract room features
        room_features = self._extract_room_features(analysis_text)
        
        # Check if this matches an existing room
        existing_room_id = self.house_map.find_room_by_features(
            room_features["objects"], analysis_text
        )
        
        if existing_room_id:
            # Update existing room
            self.house_map.update_room(existing_room_id, {
                "last_visited": datetime.now().isoformat(),
                "visit_count": self.house_map.rooms[existing_room_id].visit_count + 1
            })
            self.house_map.current_room_id = existing_room_id
            
            room_name = (self.house_map.rooms[existing_room_id].user_assigned_name or 
                        self.house_map.rooms[existing_room_id].auto_detected_type)
            
            await self.tts.speak(f"I recognize this room - it's the {room_name}.")
            
            return {
                "success": True,
                "action": "recognized_existing_room",
                "room_id": existing_room_id,
                "room_name": room_name,
                "features": room_features
            }
        else:
            # Create new room
            room_id = f"room_{int(time.time())}"
            
            new_room = RoomData(
                room_id=room_id,
                name=room_features["detected_type"],
                auto_detected_type=room_features["detected_type"],
                user_assigned_name=None,
                objects_present=room_features["objects"],
                description=analysis_text,
                confidence=room_features["confidence"],
                discovery_timestamp=datetime.now().isoformat(),
                last_visited=datetime.now().isoformat(),
                visit_count=1,
                connections=[],
                estimated_size=room_features["size"],
                distinctive_features=room_features["distinctive_features"]
            )
            
            self.house_map.add_room(new_room)
            self.house_map.current_room_id = room_id
            
            await self.tts.speak(
                f"I've discovered a new {room_features['detected_type']}! "
                f"I can see {', '.join(room_features['objects'][:3])} and other items. "
                f"You can rename this room if you'd like."
            )
            
            return {
                "success": True,
                "action": "discovered_new_room",
                "room_id": room_id,
                "room_type": room_features["detected_type"],
                "features": room_features,
                "objects_found": room_features["objects"]
            }
    
    def _extract_room_features(self, analysis_text: str) -> Dict[str, Any]:
        """Extract structured features from room analysis"""
        analysis_lower = analysis_text.lower()
        
        # Extract objects mentioned
        objects = []
        for room_type, pattern in self.room_patterns.items():
            for keyword in pattern["keywords"]:
                if keyword in analysis_lower:
                    objects.append(keyword)
        
        # Detect room type based on object patterns
        room_scores = {}
        for room_type, pattern in self.room_patterns.items():
            score = 0
            for keyword in pattern["keywords"]:
                if keyword in analysis_lower:
                    score += pattern["priority"]
            room_scores[room_type] = score
        
        # Get best match
        detected_type = max(room_scores, key=room_scores.get) if room_scores else "unknown_room"
        confidence = room_scores.get(detected_type, 0) / 5.0  # Normalize
        
        # Extract size indicators
        size = "medium"
        if any(word in analysis_lower for word in ["large", "spacious", "big"]):
            size = "large"
        elif any(word in analysis_lower for word in ["small", "compact", "tiny"]):
            size = "small"
        
        # Extract distinctive features
        distinctive_features = []
        feature_keywords = ["window", "fireplace", "chandelier", "hardwood", "carpet", "tile"]
        for keyword in feature_keywords:
            if keyword in analysis_lower:
                distinctive_features.append(keyword)
        
        return {
            "detected_type": detected_type,
            "confidence": min(1.0, confidence),
            "objects": list(set(objects)),  # Remove duplicates
            "size": size,
            "distinctive_features": distinctive_features
        }
    
    async def _show_house_map(self) -> Dict[str, Any]:
        """Show the current house map"""
        logger.info("🗺️ Displaying house map")
        
        map_summary = self.house_map.get_room_summary()
        
        if map_summary["total_rooms"] == 0:
            await self.tts.speak("I haven't discovered any rooms yet. Let me analyze this area first.")
            return await self._analyze_current_room()
        
        # Create spoken summary
        room_descriptions = []
        for room_id, room_info in map_summary["rooms"].items():
            name = room_info["name"]
            object_count = len(room_info["objects"])
            visits = room_info["visit_count"]
            
            room_descriptions.append(f"the {name} with {object_count} items, visited {visits} times")
        
        rooms_text = ", ".join(room_descriptions)
        
        await self.tts.speak(
            f"I've discovered {map_summary['total_rooms']} rooms: {rooms_text}. "
            f"I've also learned where {len(map_summary['object_patterns'])} different objects are usually found."
        )
        
        return {
            "success": True,
            "action": "map_displayed",
            "map_summary": map_summary,
            "total_rooms": map_summary["total_rooms"]
        }
    
    async def _name_room(self, room_id: str, room_name: str) -> Dict[str, Any]:
        """Assign a custom name to a room"""
        if not room_id or room_id not in self.house_map.rooms:
            available_rooms = list(self.house_map.rooms.keys())
            await self.tts.speak(f"I need a valid room ID. Available rooms: {', '.join(available_rooms)}")
            return {
                "success": False,
                "error": "Invalid room ID",
                "available_rooms": available_rooms
            }
        
        if not room_name:
            await self.tts.speak("Please provide a name for the room.")
            return {"success": False, "error": "Room name required"}
        
        # Update room name
        self.house_map.update_room(room_id, {"user_assigned_name": room_name})
        
        await self.tts.speak(f"Great! I'll now call this room the {room_name}.")
        
        return {
            "success": True,
            "action": "room_renamed",
            "room_id": room_id,
            "new_name": room_name
        }
    
    async def _explore_new_areas(self) -> Dict[str, Any]:
        """Explore to discover new rooms"""
        logger.info("🧭 Exploring for new areas")
        
        await self.tts.speak("Let me explore to find new areas of the house.")
        
        # Simple exploration pattern
        exploration_moves = [
            ("forward", 2),
            ("left_turn", 90),
            ("forward", 1),
            ("right_turn", 90),
            ("forward", 1)
        ]
        
        areas_explored = []
        
        for move_type, param in exploration_moves:
            try:
                if move_type == "forward":
                    await self.movement.move_forward(distance=param, speed=40)
                elif move_type == "left_turn":
                    await self.movement.turn(angle=-param, speed=30)
                elif move_type == "right_turn":
                    await self.movement.turn(angle=param, speed=30)
                
                # Analyze this new position
                result = await self._analyze_current_room()
                areas_explored.append(result)
                
                await asyncio.sleep(2)  # Brief pause between moves
                
            except Exception as e:
                logger.warning(f"⚠️ Exploration move failed: {e}")
                break
        
        await self.tts.speak(f"Exploration complete! I checked {len(areas_explored)} areas.")
        
        return {
            "success": True,
            "action": "exploration_complete",
            "areas_explored": len(areas_explored),
            "discoveries": areas_explored
        }