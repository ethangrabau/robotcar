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
        
        # Initialize object search if available
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
        - help: Finding objects, calling parents, practical help
        - learn: Educational content, homework, questions
        - story: Storytelling, reading, creative activities
        - respond: Simple conversation, greeting, or unclear request
        
        Respond with just the category word.
        """
        
        response = self.llm.invoke([SystemMessage(content=intent_prompt)])
        intent = response.content.strip().lower()
        
        # Validate intent
        valid_intents = ["play", "help", "learn", "story", "respond"]
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
        """Handle help requests"""
        logger.info("🤝 Entering help mode")
        
        last_message = state["messages"][-1] if state.get("messages") else ""
        
        # Check if it's about finding something
        if "find" in last_message.lower():
            # Extract what to find
            state["tool_results"] = {
                "action": "search_for_object",
                "message": "I'll help you look for that!",
                "search_active": True
            }
        elif "mom" in last_message.lower() or "dad" in last_message.lower():
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
    
    async def execute_action_node(self, state: AgentState) -> AgentState:
        """Execute the planned action with safety checks"""
        logger.info("⚙️ Executing action")
        
        tool_results = state.get("tool_results", {})
        action = tool_results.get("action", "")
        
        # Safety override for any movement
        if state.get("safety_status") == "caution":
            logger.info("🐢 Reducing speed due to nearby child")
            self.movement.set_max_speed(self.SLOW_SPEED)
        
        # Execute based on action type
        if action == "search_for_object":
            # This would trigger the object search tool
            state["tool_results"]["status"] = "searching"
        elif action == "interactive_game":
            # Start a game sequence
            if tool_results.get("game") == "simon_says":
                state["tool_results"]["status"] = "game_active"
                state["tool_results"]["next_move"] = "Simon says... touch your nose!"
        
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
    
    def route_by_intent(self, state: AgentState) -> Literal["play", "help", "learn", "story", "respond"]:
        """Route to appropriate mode based on intent"""
        mode = state.get("interaction_mode", "respond")
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