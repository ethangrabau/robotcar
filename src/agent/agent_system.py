#!/usr/bin/env python3
"""
Agent System for PiCar-X
Implements the hybrid agent-tool architecture with LLM-based reasoning
"""

import os
import sys
import time
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_system.log')
    ]
)
logger = logging.getLogger(__name__)

# Import tool registry and tools
from src.agent.tools.registry import tool_registry
from src.agent.tools.base_tool import BaseTool
from src.agent.tools.enhanced_search_tool import EnhancedSearchTool

# Import hardware integration
from src.agent.hardware_integration import (
    get_hardware, 
    get_vision_system, 
    get_obstacle_avoidance,
    cleanup_all
)

# Import memory components
from src.agent.memory.search_memory import SearchMemory

# Check for OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        from keys import OPENAI_API_KEY
    except ImportError:
        logger.warning("OpenAI API key not found in environment or keys.py")
        OPENAI_API_KEY = None

class AgentSystem:
    """
    Main agent system for PiCar-X
    Implements the hybrid agent-tool architecture
    """
    
    def __init__(self):
        """Initialize the agent system"""
        self.hardware = get_hardware()
        self.vision = get_vision_system()
        self.memory = SearchMemory()
        self.tools = {}
        self.initialized = False
        
        # OpenAI client for LLM reasoning
        self.openai_client = None
        if OPENAI_API_KEY:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def initialize(self):
        """Initialize the agent system and register tools"""
        logger.info("Initializing agent system")
        
        # Register tools
        self._register_tools()
        
        self.initialized = True
        logger.info("Agent system initialized")
        return True
    
    def _register_tools(self):
        """Register all available tools"""
        # Register the enhanced search tool
        search_tool = EnhancedSearchTool(
            car=self.hardware,
            vision_system=self.vision,
            memory=self.memory
        )
        
        # Add to our local tools dictionary
        self.tools['search'] = search_tool
        
        # Register with the global tool registry
        tool_registry.register_tool(search_tool)
        
        logger.info(f"Registered tools: {list(tool_registry.list_tools())}")
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool by name"""
        if not self.initialized:
            logger.error("Agent system not initialized")
            return {"status": "error", "message": "Agent system not initialized"}
        
        # Get the tool from the registry
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool '{tool_name}' not found")
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}
        
        try:
            logger.info(f"Executing tool '{tool_name}' with args: {kwargs}")
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def search_for_object(self, object_name: str, timeout: int = 60) -> Dict[str, Any]:
        """Convenience method to search for an object"""
        return await self.execute_tool(
            tool_name="search_for_object",
            object_name=object_name,
            timeout=timeout
        )
    
    async def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language command using LLM reasoning
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available, using rule-based command processing")
            return await self._rule_based_command_processing(command)
        
        try:
            # Prepare the tools for function calling
            tools = []
            for tool_name in tool_registry.list_tools():
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object",
                                "properties": tool.parameters,
                                "required": [
                                    param for param, details in tool.parameters.items()
                                    if details.get("required", True)
                                ]
                            }
                        }
                    })
            
            # Call the OpenAI API for tool selection
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant controlling a PiCar-X robot. Select the appropriate tool to execute the user's command."},
                    {"role": "user", "content": command}
                ],
                tools=tools,
                tool_choice="auto"
            )
            
            # Extract the tool call
            message = response.choices[0].message
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"LLM selected tool '{tool_name}' with args: {tool_args}")
                return await self.execute_tool(tool_name, **tool_args)
            else:
                logger.warning("LLM did not select a tool")
                return {"status": "error", "message": "Could not determine appropriate action"}
                
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return await self._rule_based_command_processing(command)
    
    async def _rule_based_command_processing(self, command: str) -> Dict[str, Any]:
        """
        Simple rule-based command processing as fallback
        """
        command = command.lower().strip()
        
        # Check for search commands
        search_keywords = ["find", "search", "look for", "where is", "locate"]
        for keyword in search_keywords:
            if keyword in command:
                # Extract the object name after the keyword
                parts = command.split(keyword, 1)
                if len(parts) > 1:
                    object_name = parts[1].strip()
                    if object_name:
                        logger.info(f"Rule-based processing detected search for '{object_name}'")
                        return await self.search_for_object(object_name)
        
        # Default response
        return {
            "status": "error", 
            "message": "Could not understand command. Try 'find [object]'"
        }
    
    def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up agent system")
        cleanup_all()

# Singleton instance
_agent_system = None

def get_agent_system():
    """Get or create the agent system singleton"""
    global _agent_system
    if _agent_system is None:
        _agent_system = AgentSystem()
        _agent_system.initialize()
    return _agent_system

async def process_command(command: str) -> Dict[str, Any]:
    """Helper function to process a command"""
    agent = get_agent_system()
    return await agent.process_command(command)
