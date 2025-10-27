from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar('T', bound='BaseTool')

class ToolExecutionError(Exception):
    """Exception raised when a tool fails to execute."""
    def __init__(self, message: str, tool_name: Optional[str] = None):
        self.tool_name = tool_name
        self.message = message
        super().__init__(self.message)

class BaseTool(ABC):
    """Base class for all tools in the agent system.
    
    Tools can be high-level (task-oriented) or low-level (direct hardware control).
    """
    
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def __init_subclass__(cls, **kwargs):
        """Register the tool in the registry when subclassed."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'name') and cls.name:
            from .registry import ToolRegistry
            ToolRegistry.register_tool(cls)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create a tool instance from a dictionary."""
        return cls(**data)
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with the given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            The result of the tool execution
        """
        pass
    
    def validate_parameters(self, **kwargs) -> bool:
        """Validate the provided parameters against the tool's schema."""
        if not hasattr(self, 'parameters'):
            return True
            
        for param, param_info in self.parameters.items():
            if param_info.get('required', False) and param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
                
            param_type = param_info.get('type')
            if param in kwargs and param_type:
                if not isinstance(kwargs[param], param_type):
                    try:
                        kwargs[param] = param_type(kwargs[param])
                    except (TypeError, ValueError):
                        raise ValueError(f"Parameter {param} must be of type {param_type.__name__}")
        
        return True
