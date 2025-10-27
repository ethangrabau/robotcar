import time
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass, field

@dataclass
class SearchArea:
    """Represents a search area with position and dimensions."""
    x: float
    y: float
    width: float
    height: float
    last_searched: float = field(default_factory=time.time)
    search_count: int = 0
    
    def contains(self, x: float, y: float) -> bool:
        """Check if a point is within this search area."""
        return (self.x <= x < self.x + self.width and 
                self.y <= y < self.y + self.height)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'last_searched': self.last_searched,
            'search_count': self.search_count
        }

class SearchMemory:
    """Tracks search progress and remembers visited locations."""
    
    def __init__(self, decay_rate: float = 0.95):
        """Initialize search memory.
        
        Args:
            decay_rate: How quickly to forget old searches (0-1, higher = remember longer)
        """
        self.search_areas: List[SearchArea] = []
        self.object_locations: Dict[str, List[Dict]] = {}
        self.decay_rate = decay_rate
        self.current_search_area: Optional[SearchArea] = None
    
    def add_search_area(self, x: float, y: float, width: float, height: float) -> SearchArea:
        """Add a new search area."""
        area = SearchArea(x, y, width, height)
        self.search_areas.append(area)
        return area
    
    def get_least_searched_area(self) -> Optional[SearchArea]:
        """Get the area that has been searched the least recently."""
        if not self.search_areas:
            return None
            
        # Sort by last_searched and search_count
        return min(self.search_areas, key=lambda a: (a.last_searched, a.search_count))
    
    def record_visit(self, x: float, y: float) -> None:
        """Record a visit to a location."""
        now = time.time()
        
        # Update existing area if point is inside it
        for area in self.search_areas:
            if area.contains(x, y):
                area.last_searched = now
                area.search_count += 1
                return
        
        # If not in any area, create a new small area
        self.add_search_area(x - 0.1, y - 0.1, 0.2, 0.2)
    
    def remember_object_location(self, object_name: str, x: float, y: float, 
                              confidence: float = 1.0) -> None:
        """Remember the location of an object."""
        if object_name not in self.object_locations:
            self.object_locations[object_name] = []
            
        self.object_locations[object_name].append({
            'x': x,
            'y': y,
            'confidence': confidence,
            'timestamp': time.time()
        })
    
    def recall_object_location(self, object_name: str) -> Optional[Tuple[float, float, float]]:
        """Recall the most likely location of an object."""
        if object_name not in self.object_locations or not self.object_locations[object_name]:
            return None
            
        # Get most recent sighting
        recent = max(self.object_locations[object_name], key=lambda x: x['timestamp'])
        return (recent['x'], recent['y'], recent['confidence'])
    
    def decay_memory(self) -> None:
        """Apply decay to memory to forget old information."""
        # Remove old object locations
        current_time = time.time()
        for obj_name, locations in list(self.object_locations.items()):
            # Filter out old entries
            self.object_locations[obj_name] = [
                loc for loc in locations 
                if (current_time - loc['timestamp']) < (86400 / self.decay_rate)  # 1 day / decay_rate
            ]
            
            # Remove object if no locations left
            if not self.object_locations[obj_name]:
                del self.object_locations[obj_name]
