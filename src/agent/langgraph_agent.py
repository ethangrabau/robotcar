#!/usr/bin/env python3
"""
LangGraph-based Agent System for Family Robot Assistant

This implements a stateful, graph-based agent architecture that integrates
all robot capabilities including movement, vision, and object search.
"""

import asyncio
import logging
from typing import Dict, Any, List, TypedDict, Annotated, Literal, Optional
from enum import Enum
import os
from datetime import datetime
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Import ALL existing tools and capabilities
from .tools.vision_tools import AnalyzeSceneTool
from .tools.persistent_search_tool import PersistentSearchTool
from .tools.room_discovery_tool import RoomDiscoveryTool
from .tools.smart_search_router import SmartSearchRouter
try:
    from .tools.object_search_tool import ObjectSearchTool
except ImportError:
    # Try alternative import if module structure differs
    from ..tools.object_search_tool import ObjectSearchTool

# Import movement and hardware control
try:
    from ..movement.controller import MovementController
except ImportError:
    # Fallback for testing
    class MovementController:
        def __init__(self):
            pass
        async def move_forward(self, distance=1, speed=50):
            return {"status": "moved", "distance": distance}
        async def turn(self, angle=90, speed=50):
            return {"status": "turned", "angle": angle}
        async def stop(self):
            return {"status": "stopped"}

# Import camera for direct hardware access
try:
    from ..vision.camera import Camera
except ImportError:
    class Camera:
        def __init__(self):
            pass
        def capture_frame(self):
            return None

logger = logging.getLogger(__name__)

# State definition for the graph
class AgentState(TypedDict):
    """State that flows through the agent graph"""
    messages: List[Any]  # Conversation history
    current_user: str  # Who's interacting (child name or "unknown")
    current_activity: str  # What the robot is doing
    emotion_state: str  # Detected emotional state of child
    interaction_mode: str  # "play", "help", "learn", "idle", "search", "navigate"
    tool_results: Dict[str, Any]  # Results from tool executions
    last_vision: Optional[str]  # Last vision analysis result
    search_target: Optional[str]  # What we're looking for
    navigation_target: Optional[str]  # Where we're going
    hardware_status: Dict[str, Any]  # Current hardware state

class InteractionMode(Enum):
    """Modes of robot interaction"""
    PLAY = "play"
    HELP = "help" 
    LEARN = "learn"
    STORY = "story"
    IDLE = "idle"
    SEARCH = "search"  # Object search mode
    NAVIGATE = "navigate"  # Navigation mode
    EXPLORE = "explore"  # Free exploration

class FamilyRobotGraph:
    """Main graph-based agent for family interactions"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
        # Initialize ALL robot tools
        self.vision_tool = AnalyzeSceneTool()
        self.movement = MovementController()
        self.camera = Camera()
        
        # Initialize enhanced search and mapping tools
        self.persistent_search = PersistentSearchTool()
        self.room_discovery = RoomDiscoveryTool()
        self.smart_router = SmartSearchRouter()
        
        # Initialize legacy object search if available
        try:
            self.object_search = ObjectSearchTool()
        except Exception as e:
            logger.warning(f"ObjectSearchTool not available: {e}")
            self.object_search = None
        
        self.checkpointer = MemorySaver()  # For conversation memory
        
        # Robot capabilities flags
        self.capabilities = {
            "vision": True,
            "movement": True,
            "object_search": self.object_search is not None,
            "persistent_search": True,
            "smart_routing": True,
            "room_mapping": True,
            "speech": True
        }
        
        # Build the graph
        self.graph = self._build_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes for all capabilities
        workflow.add_node("perceive", self.perceive_node)  # Vision/sensor input
        workflow.add_node("identify_user", self.identify_user_node)
        workflow.add_node("understand_intent", self.understand_intent_node)
        workflow.add_node("play_mode", self.play_mode_node)
        workflow.add_node("help_mode", self.help_mode_node)
        workflow.add_node("learn_mode", self.learn_mode_node)
        workflow.add_node("story_mode", self.story_mode_node)
        workflow.add_node("search_mode", self.search_mode_node)  # Object search
        workflow.add_node("navigate_mode", self.navigate_mode_node)  # Navigation
        workflow.add_node("explore_mode", self.explore_mode_node)  # Room discovery
        workflow.add_node("execute_action", self.execute_action_node)
        workflow.add_node("respond", self.respond_node)
        
        # Set entry point
        workflow.set_entry_point("perceive")
        
        # Add edges (the flow between nodes)
        workflow.add_edge("perceive", "identify_user")
        workflow.add_edge("identify_user", "understand_intent")
        
        # Conditional routing based on intent
        workflow.add_conditional_edges(
            "understand_intent",
            self.route_by_intent,
            {
                "play": "play_mode",
                "help": "help_mode",
                "learn": "learn_mode",
                "story": "story_mode",
                "search": "search_mode",
                "navigate": "navigate_mode",
                "explore": "explore_mode",
                "respond": "respond",
            }
        )
        
        # All activity modes lead to execution
        workflow.add_edge("play_mode", "execute_action")
        workflow.add_edge("help_mode", "execute_action")
        workflow.add_edge("learn_mode", "execute_action")
        workflow.add_edge("story_mode", "execute_action")
        workflow.add_edge("search_mode", "execute_action")
        workflow.add_edge("navigate_mode", "execute_action")
        workflow.add_edge("explore_mode", "execute_action")
        
        # Execution leads to response
        workflow.add_edge("execute_action", "respond")
        
        # Response can loop back to perceive or end
        workflow.add_conditional_edges(
            "respond",
            self.should_continue,
            {
                "continue": "perceive",
                "end": END,
            }
        )
        
        return workflow
    
    async def perceive_node(self, state: AgentState) -> AgentState:
        """Perceive environment using sensors and camera"""
        logger.info("👁️ Perceiving environment")
        
        # Take a snapshot of current environment
        try:
            scene_analysis = await self.vision_tool.execute(
                query="Describe what you see. Include any objects, people, or interesting features.",
                save_image=False
            )
            state["last_vision"] = scene_analysis.get("analysis", "")
            logger.info(f"Vision: {state['last_vision'][:100]}...")
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            state["last_vision"] = "Unable to analyze scene"
        
        # Update hardware status
        state["hardware_status"] = {
            "camera": "active",
            "movement": "ready",
            "timestamp": datetime.now().isoformat()
        }
        
        return state
    
    async def identify_user_node(self, state: AgentState) -> AgentState:
        """Identify who we're talking to"""
        logger.info("👤 Identifying user")
        
        # Use vision to check for faces
        face_analysis = await self.vision_tool.execute(
            query="Describe any people you see. Focus on apparent age (child/adult) and any distinguishing features.",
            save_image=True,
            image_dir="family_interactions"
        )
        
        analysis_text = face_analysis.get("analysis", "").lower()
        
        # Simple classification for now
        if "child" in analysis_text or "kid" in analysis_text:
            state["current_user"] = "child"
            # Try to detect emotion
            if "smiling" in analysis_text or "happy" in analysis_text:
                state["emotion_state"] = "happy"
            elif "crying" in analysis_text or "sad" in analysis_text:
                state["emotion_state"] = "sad"
            else:
                state["emotion_state"] = "neutral"
        else:
            state["current_user"] = "adult"
            state["emotion_state"] = "neutral"
        
        return state
    
    async def understand_intent_node(self, state: AgentState) -> AgentState:
        """Understand what the user wants"""
        logger.info("🤔 Understanding intent")
        
        if not state.get("messages"):
            state["messages"] = []
            return state
        
        last_message = state["messages"][-1] if state["messages"] else ""
        
        # Use LLM to classify intent
        intent_prompt = f"""
        You are a friendly family robot. Analyze this request from a {state.get('current_user', 'person')}:
        "{last_message}"
        
        Classify the intent as one of:
        - play: Games, fun activities, hide and seek, etc.
        - help: General help or assistance
        - search: Finding specific objects ("find my keys", "where is my backpack")
        - navigate: Moving to specific locations ("go to the kitchen", "come here")
        - explore: Mapping, room discovery ("explore the house", "show me the map", "what rooms have you found")
        - learn: Educational content, homework, questions
        - story: Storytelling, reading, creative activities
        - respond: Simple conversation, greeting, or unclear request
        
        Respond with just the category word.
        """
        
        response = self.llm.invoke([SystemMessage(content=intent_prompt)])
        intent = response.content.strip().lower()
        
        # Check for explicit keywords that override LLM classification
        message_lower = last_message.lower() if isinstance(last_message, str) else str(last_message).lower()
        if "find" in message_lower or "where is" in message_lower or "look for" in message_lower:
            intent = "search"
        elif "go to" in message_lower or "come here" in message_lower or "move to" in message_lower:
            intent = "navigate"
        elif "explore" in message_lower or "map" in message_lower or "rooms" in message_lower or "house" in message_lower:
            intent = "explore"
        
        # Validate intent
        valid_intents = ["play", "help", "search", "navigate", "explore", "learn", "story", "respond"]
        if intent not in valid_intents:
            intent = "respond"
        
        state["interaction_mode"] = intent
        logger.info(f"📋 Detected intent: {intent}")
        
        return state
    
    async def play_mode_node(self, state: AgentState) -> AgentState:
        """Handle play interactions"""
        logger.info("🎮 Entering play mode")
        
        if state.get("current_user") != "child":
            state["tool_results"] = {
                "action": "request_parent_approval",
                "message": "I'd love to play! Can you ask your parents if it's okay?"
            }
            state["parent_approved"] = False
            return state
        
        # Safe play activities based on emotion
        if state.get("emotion_state") == "sad":
            state["tool_results"] = {
                "action": "cheer_up_game",
                "message": "Let's play a fun game to cheer you up! How about Simon Says?",
                "game": "simon_says"
            }
        else:
            state["tool_results"] = {
                "action": "interactive_game",
                "message": "Let's play! I can count while you hide, or we can play Simon Says!",
                "game": "hide_and_seek"
            }
        
        state["current_activity"] = "playing"
        return state
    
    async def help_mode_node(self, state: AgentState) -> AgentState:
        """Handle general help requests"""
        logger.info("🤝 Entering help mode")
        
        last_message = state["messages"][-1] if state.get("messages") else ""
        message_str = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
        
        if "mom" in message_str.lower() or "dad" in message_str.lower():
            state["tool_results"] = {
                "action": "call_parent",
                "message": "I'll let them know you're looking for them!"
            }
        else:
            state["tool_results"] = {
                "action": "general_help",
                "message": "I'm here to help! What do you need?"
            }
        
        state["current_activity"] = "helping"
        return state
    
    async def learn_mode_node(self, state: AgentState) -> AgentState:
        """Handle educational interactions"""
        logger.info("📚 Entering learn mode")
        
        state["tool_results"] = {
            "action": "educational_content",
            "message": "Let's learn something fun! I can help with counting, colors, or answer questions!",
            "activity": "interactive_learning"
        }
        
        state["current_activity"] = "teaching"
        return state
    
    async def story_mode_node(self, state: AgentState) -> AgentState:
        """Handle story time"""
        logger.info("📖 Entering story mode")
        
        state["tool_results"] = {
            "action": "storytelling",
            "message": "I love stories! Should I tell you a story about a brave robot, or would you like to create one together?",
            "story_type": "interactive"
        }
        
        state["current_activity"] = "storytelling"
        return state
    
    async def search_mode_node(self, state: AgentState) -> AgentState:
        """Handle object search requests using persistent search"""
        logger.info("🔍 Entering enhanced search mode")
        
        last_message = state["messages"][-1] if state.get("messages") else ""
        message_str = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
        
        # Extract object to search for
        search_terms = ["find", "where is", "look for", "search for"]
        object_to_find = None
        
        for term in search_terms:
            if term in message_str.lower():
                # Extract object name after the search term
                parts = message_str.lower().split(term)
                if len(parts) > 1:
                    object_to_find = parts[1].strip().rstrip('?!.').lstrip('my ').lstrip('the ')
                    break
        
        if object_to_find:
            state["search_target"] = object_to_find
            # Check if we have learned patterns for smarter search
            has_learned_patterns = len(self.room_discovery.house_map.object_locations) > 0
            
            if has_learned_patterns:
                state["tool_results"] = {
                    "action": "smart_search",
                    "message": f"I'll use what I've learned to search intelligently for the {object_to_find}. Let me check the most likely locations first!",
                    "target": object_to_find,
                    "search_type": "smart_routing",
                    "search_active": True
                }
            else:
                state["tool_results"] = {
                    "action": "persistent_search",
                    "message": f"I'll search systematically for the {object_to_find}. I won't give up until I find it or check everywhere possible!",
                    "target": object_to_find,
                    "search_type": "persistent",
                    "search_active": True
                }
            state["current_activity"] = "persistent_searching"
        else:
            state["tool_results"] = {
                "action": "clarify_search",
                "message": "What would you like me to find?"
            }
            state["current_activity"] = "waiting_for_clarification"
        
        return state
    
    async def navigate_mode_node(self, state: AgentState) -> AgentState:
        """Handle navigation requests"""
        logger.info("🗺️ Entering navigation mode")
        
        last_message = state["messages"][-1] if state.get("messages") else ""
        message_str = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
        
        # Parse navigation commands
        if "come here" in message_str.lower():
            state["tool_results"] = {
                "action": "come_to_user",
                "message": "I'm coming to you!",
                "movement": "approach_person"
            }
        elif "go to" in message_str.lower():
            # Extract location
            parts = message_str.lower().split("go to")
            if len(parts) > 1:
                location = parts[1].strip().rstrip('!.').lstrip('the ')
                state["navigation_target"] = location
                state["tool_results"] = {
                    "action": "navigate_to_location",
                    "message": f"I'll go to the {location}!",
                    "destination": location
                }
        elif "follow me" in message_str.lower():
            state["tool_results"] = {
                "action": "follow_mode",
                "message": "I'll follow you!",
                "movement": "follow"
            }
        elif "stop" in message_str.lower():
            state["tool_results"] = {
                "action": "stop_movement",
                "message": "Stopping now!",
                "movement": "stop"
            }
        else:
            # General movement
            state["tool_results"] = {
                "action": "explore",
                "message": "I'll explore around!",
                "movement": "explore"
            }
        
        state["current_activity"] = "navigating"
        return state
    
    async def explore_mode_node(self, state: AgentState) -> AgentState:
        """Handle room discovery and mapping requests"""
        logger.info("🗺️ Entering exploration mode")
        
        last_message = state["messages"][-1] if state.get("messages") else ""
        message_str = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
        
        # Determine exploration action based on user request
        if "map" in message_str.lower() or "rooms" in message_str.lower():
            state["tool_results"] = {
                "action": "show_map",
                "message": "Let me show you what I've discovered about the house!",
                "exploration_type": "show_map"
            }
        elif "explore" in message_str.lower() or "discover" in message_str.lower():
            state["tool_results"] = {
                "action": "explore_new",
                "message": "I'll explore to discover new areas of the house!",
                "exploration_type": "discover_new"
            }
        elif "this room" in message_str.lower() or "analyze" in message_str.lower():
            state["tool_results"] = {
                "action": "analyze_current",
                "message": "Let me analyze this room and add it to my map!",
                "exploration_type": "analyze_current"
            }
        else:
            # Default to analyzing current room
            state["tool_results"] = {
                "action": "analyze_current",
                "message": "Let me analyze this area and see what I can learn about it!",
                "exploration_type": "analyze_current"
            }
        
        state["current_activity"] = "exploring"
        return state
    
    async def execute_action_node(self, state: AgentState) -> AgentState:
        """Execute the planned action using actual robot hardware"""
        logger.info("⚙️ Executing action")
        
        tool_results = state.get("tool_results", {})
        action = tool_results.get("action", "")
        
        try:
            # Smart search with learning
            if action == "smart_search":
                target = tool_results.get("target", "object")
                logger.info(f"🧠 Starting smart search for: {target}")
                
                # Use the SmartSearchRouter
                search_result = await self.smart_router.execute(
                    object_name=target,
                    use_learning=True,
                    max_search_time=300
                )
                
                if search_result.get("found"):
                    state["tool_results"]["status"] = "found"
                    state["tool_results"]["message"] = f"Found the {target}! My learning paid off - {search_result.get('search_strategy', 'smart search')} worked!"
                    state["tool_results"]["location"] = search_result.get("location")
                    state["tool_results"]["search_strategy"] = search_result.get("search_strategy")
                else:
                    state["tool_results"]["status"] = "not_found_smart_search"
                    state["tool_results"]["message"] = f"Completed intelligent search for {target}. {search_result.get('message', 'Search complete.')}"
                    state["tool_results"]["search_strategy"] = search_result.get("search_strategy")
            
            # Enhanced persistent search actions
            elif action == "persistent_search":
                target = tool_results.get("target", "object")
                logger.info(f"🔍 Starting persistent search for: {target}")
                
                # Use the new PersistentSearchTool
                search_result = await self.persistent_search.execute(
                    object_name=target,
                    max_total_time=300,  # 5 minutes max
                    announce_progress=True
                )
                
                if search_result.get("found"):
                    state["tool_results"]["status"] = "found"
                    state["tool_results"]["message"] = f"Successfully found the {target} using {search_result.get('strategy_used')} strategy!"
                    state["tool_results"]["location"] = search_result.get("location")
                    state["tool_results"]["areas_searched"] = search_result.get("areas_searched", [])
                    
                    # Learn this object location for future searches
                    current_room = state.get("current_room_id")
                    if current_room:
                        self.room_discovery.house_map.learn_object_location(target, current_room)
                else:
                    state["tool_results"]["status"] = "not_found_after_thorough_search"
                    state["tool_results"]["message"] = f"I searched thoroughly for the {target} in {len(search_result.get('areas_searched', []))} areas but couldn't find it. {search_result.get('recommendation', '')}"
                    state["tool_results"]["areas_searched"] = search_result.get("areas_searched", [])
            
            # Room discovery and mapping actions
            elif action in ["show_map", "analyze_current", "explore_new"]:
                logger.info(f"🗺️ Executing room discovery action: {action}")
                
                discovery_result = await self.room_discovery.execute(action=action)
                
                state["tool_results"]["status"] = "completed"
                state["tool_results"]["discovery_result"] = discovery_result
                
                if action == "analyze_current":
                    if discovery_result.get("action") == "discovered_new_room":
                        state["current_room_id"] = discovery_result.get("room_id")
                        state["tool_results"]["message"] = f"I've discovered this is a {discovery_result.get('room_type')}! I found {len(discovery_result.get('objects_found', []))} items here."
                    elif discovery_result.get("action") == "recognized_existing_room":
                        state["current_room_id"] = discovery_result.get("room_id")
                        state["tool_results"]["message"] = f"I recognize this room - it's the {discovery_result.get('room_name')}!"
                
                elif action == "show_map":
                    map_summary = discovery_result.get("map_summary", {})
                    state["tool_results"]["message"] = f"I've mapped {map_summary.get('total_rooms', 0)} rooms and learned where {len(map_summary.get('object_patterns', {}))} types of objects are usually found."
                
                elif action == "explore_new":
                    areas_explored = discovery_result.get("areas_explored", 0)
                    state["tool_results"]["message"] = f"Exploration complete! I checked {areas_explored} new areas."
            
            # Navigation actions
            elif action == "come_to_user":
                # Move toward where we last saw a person
                await self.movement.move_forward(distance=1, speed=50)
                state["tool_results"]["status"] = "moving"
            
            elif action == "navigate_to_location":
                destination = tool_results.get("destination")
                logger.info(f"📍 Navigating to: {destination}")
                
                # Simple navigation - in reality would use mapping
                await self.movement.turn(angle=45, speed=50)
                await self.movement.move_forward(distance=2, speed=50)
                state["tool_results"]["status"] = "arrived"
                state["tool_results"]["message"] = f"I've arrived at the {destination}!"
            
            elif action == "stop_movement":
                await self.movement.stop()
                state["tool_results"]["status"] = "stopped"
            
            elif action == "follow_mode":
                # Start follow mode - would use vision to track person
                state["tool_results"]["status"] = "following"
                logger.info("👣 Following mode activated")
            
            # Game actions
            elif action == "interactive_game":
                game = tool_results.get("game")
                if game == "simon_says":
                    # Import and use the Simon Says game tool
                    from .tools.child_interaction_tools import SimonSaysGame
                    simon_game = SimonSaysGame()
                    game_result = await simon_game.execute(difficulty="easy", rounds=3)
                    state["tool_results"]["status"] = "game_complete"
                    state["tool_results"]["score"] = game_result.get("score", 0)
                elif game == "hide_and_seek":
                    from .tools.child_interaction_tools import HideAndSeekGame
                    hide_seek = HideAndSeekGame()
                    game_result = await hide_seek.execute(count_time=10, search_time=60)
                    state["tool_results"]["status"] = "game_complete"
            
            # Story actions
            elif action == "storytelling":
                from .tools.child_interaction_tools import StorytellingTool
                storyteller = StorytellingTool()
                story_result = await storyteller.execute(
                    story_type=tool_results.get("story_type", "premade"),
                    theme="adventure"
                )
                state["tool_results"]["status"] = "story_told"
            
            # Default/unknown actions
            else:
                logger.info(f"📝 Action '{action}' noted but not executed")
                state["tool_results"]["status"] = "acknowledged"
        
        except Exception as e:
            logger.error(f"❌ Error executing action {action}: {e}")
            state["tool_results"]["status"] = "error"
            state["tool_results"]["error"] = str(e)
        
        return state
    
    async def respond_node(self, state: AgentState) -> AgentState:
        """Generate and deliver response"""
        logger.info("💬 Generating response")
        
        # Add response to messages
        tool_results = state.get("tool_results", {})
        response_message = tool_results.get("message", "I'm here to help!")
        
        if not state.get("messages"):
            state["messages"] = []
        
        state["messages"].append(AIMessage(content=response_message))
        
        # Log the response
        logger.info(f"🤖 Response: {response_message}")
        
        return state
    
    def route_by_intent(self, state: AgentState) -> Literal["play", "help", "search", "navigate", "explore", "learn", "story", "respond"]:
        """Route to appropriate mode based on intent"""
        mode = state.get("interaction_mode", "respond")
        # Ensure mode is valid
        valid_modes = ["play", "help", "search", "navigate", "explore", "learn", "story", "respond"]
        if mode not in valid_modes:
            mode = "respond"
        return mode
    
    def should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Decide whether to continue interaction"""
        # End if explicitly requested or after certain activities
        if state.get("messages"):
            last_msg = str(state["messages"][-1].content).lower()
            if "bye" in last_msg or "stop" in last_msg or "end" in last_msg:
                return "end"
        
        # Continue by default for ongoing interactions
        return "continue" if state.get("current_activity") != "idle" else "end"

    async def run(self, user_input: str, thread_id: str = "default"):
        """Run the graph with user input"""
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_user": "unknown",
            "safety_status": "unknown",
            "current_activity": "idle",
            "emotion_state": "neutral",
            "interaction_mode": "idle",
            "tool_results": {},
            "parent_approved": False,
            "distance_to_human": 3.0
        }
        
        # Run with checkpointing for memory
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.app.ainvoke(initial_state, config)
        
        return result

async def main():
    """Test the LangGraph agent"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the graph
    robot = FamilyRobotGraph()
    
    # Test interactions
    test_inputs = [
        "Hi robot! Want to play?",
        "Can you find my teddy bear?",
        "Tell me a story!",
        "Help me with counting to 10"
    ]
    
    print("\n🤖 Family Robot Assistant (LangGraph Edition)\n")
    print("=" * 50)
    
    for test_input in test_inputs:
        print(f"\n👦 Child: {test_input}")
        result = await robot.run(test_input, thread_id="test_child")
        
        # Extract response
        if result.get("messages"):
            for msg in result["messages"]:
                if isinstance(msg, AIMessage):
                    print(f"🤖 Robot: {msg.content}")
        
        print("-" * 30)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())