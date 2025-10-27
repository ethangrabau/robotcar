from typing import Dict, Type, Optional, List, Any
from .base_tool import BaseTool

class ToolRegistry:
    """Registry for all available tools in the agent system."""
    
    _instance = None
    _tools: Dict[str, Type[BaseTool]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def register_tool(cls, tool_cls: Type[BaseTool]) -> None:
        """Register a tool class in the registry."""
        if not issubclass(tool_cls, BaseTool):
            raise TypeError(f"{tool_cls.__name__} is not a subclass of BaseTool")
        
        if not hasattr(tool_cls, 'name') or not tool_cls.name:
            raise ValueError(f"Tool class {tool_cls.__name__} must define a 'name' class variable")
            
        cls._tools[tool_cls.name] = tool_cls
    
    @classmethod
    def get_tool_class(cls, tool_name: str) -> Optional[Type[BaseTool]]:
        """Get a tool class by name."""
        return cls._tools.get(tool_name)
    
    @classmethod
    def create_tool(cls, tool_name: str, **kwargs) -> Optional[BaseTool]:
        """Create a tool instance by name with the given parameters."""
        tool_cls = cls.get_tool_class(tool_name)
        if tool_cls is None:
            return None
        return tool_cls(**kwargs)
    
    @classmethod
    def get_available_tools(cls) -> List[Dict[str, Any]]:
        """Get a list of all available tools with their schemas."""
        tools = []
        for name, tool_cls in cls._tools.items():
            tool_info = {
                'name': name,
                'description': getattr(tool_cls, 'description', ''),
                'parameters': getattr(tool_cls, 'parameters', {})
            }
            tools.append(tool_info)
        return tools
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered tools. Mainly for testing."""
        cls._tools = {}

# Create a singleton instance
tool_registry = ToolRegistry()
