#!/usr/bin/env python3
"""
Unit tests for the LangGraph-based Family Robot Agent

Tests core functionality including intent classification, routing, 
state management, and hardware integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.agent.langgraph_agent import FamilyRobotGraph, AgentState
    from langchain_core.messages import HumanMessage, AIMessage
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}")
    
    # Try alternative import for testing
    import importlib.util
    agent_file = project_root / "src" / "agent" / "langgraph_agent.py"
    if agent_file.exists():
        spec = importlib.util.spec_from_file_location("langgraph_agent", agent_file)
        langgraph_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(langgraph_module)
        FamilyRobotGraph = langgraph_module.FamilyRobotGraph
        AgentState = langgraph_module.AgentState
    else:
        pytest.skip("Cannot import langgraph_agent module")
    
    # Mock langchain imports for testing
    class HumanMessage:
        def __init__(self, content):
            self.content = content
    
    class AIMessage:
        def __init__(self, content):
            self.content = content

class TestFamilyRobotGraph:
    """Test the main FamilyRobotGraph class"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('src.agent.langgraph_agent.ChatOpenAI') as mock_llm, \
             patch('src.agent.langgraph_agent.AnalyzeSceneTool') as mock_vision, \
             patch('src.agent.langgraph_agent.MovementController') as mock_movement, \
             patch('src.agent.langgraph_agent.Camera') as mock_camera, \
             patch('src.agent.langgraph_agent.ObjectSearchTool') as mock_search:
            
            # Setup mocks
            mock_llm_instance = Mock()
            mock_llm_instance.invoke = AsyncMock()
            mock_llm.return_value = mock_llm_instance
            
            mock_vision_instance = Mock()
            mock_vision_instance.execute = AsyncMock()
            mock_vision.return_value = mock_vision_instance
            
            mock_movement_instance = Mock()
            mock_movement_instance.move_forward = AsyncMock()
            mock_movement_instance.turn = AsyncMock()
            mock_movement_instance.stop = AsyncMock()
            mock_movement.return_value = mock_movement_instance
            
            mock_camera_instance = Mock()
            mock_camera.return_value = mock_camera_instance
            
            mock_search_instance = Mock()
            mock_search_instance.execute = AsyncMock()
            mock_search.return_value = mock_search_instance
            
            yield {
                'llm': mock_llm_instance,
                'vision': mock_vision_instance,
                'movement': mock_movement_instance,
                'camera': mock_camera_instance,
                'search': mock_search_instance
            }
    
    @pytest.fixture
    def robot_agent(self, mock_dependencies):
        """Create FamilyRobotGraph instance with mocked dependencies"""
        return FamilyRobotGraph()
    
    def test_initialization(self, robot_agent):
        """Test that the robot initializes correctly"""
        assert robot_agent is not None
        assert hasattr(robot_agent, 'vision_tool')
        assert hasattr(robot_agent, 'movement')
        assert hasattr(robot_agent, 'camera')
        assert hasattr(robot_agent, 'capabilities')
        assert robot_agent.capabilities['vision'] == True
        assert robot_agent.capabilities['movement'] == True
    
    @pytest.mark.asyncio
    async def test_perceive_node(self, robot_agent, mock_dependencies):
        """Test the perceive node functionality"""
        # Mock vision analysis
        mock_dependencies['vision'].execute.return_value = {
            'analysis': 'I see a person standing in a living room with some furniture.'
        }
        
        initial_state = {
            'messages': [],
            'hardware_status': {}
        }
        
        result = await robot_agent.perceive_node(initial_state)
        
        assert 'last_vision' in result
        assert 'person' in result['last_vision']
        assert 'hardware_status' in result
        assert result['hardware_status']['camera'] == 'active'
        mock_dependencies['vision'].execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_identify_user_node(self, robot_agent, mock_dependencies):
        """Test user identification functionality"""
        # Mock vision analysis for child detection
        mock_dependencies['vision'].execute.return_value = {
            'analysis': 'I see a smiling child with brown hair wearing a blue shirt.'
        }
        
        initial_state = {
            'messages': [],
            'current_user': 'unknown'
        }
        
        result = await robot_agent.identify_user_node(initial_state)
        
        assert result['current_user'] == 'child'
        assert result['emotion_state'] == 'happy'
    
    @pytest.mark.asyncio
    async def test_understand_intent_node(self, robot_agent, mock_dependencies):
        """Test intent classification"""
        # Mock LLM response for intent classification
        mock_response = Mock()
        mock_response.content = 'search'
        mock_dependencies['llm'].invoke.return_value = mock_response
        
        state = {
            'messages': [HumanMessage(content="Find my backpack")],
            'current_user': 'child'
        }
        
        result = await robot_agent.understand_intent_node(state)
        
        assert result['interaction_mode'] == 'search'
        mock_dependencies['llm'].invoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_mode_node(self, robot_agent):
        """Test search mode functionality"""
        state = {
            'messages': [HumanMessage(content="Find my teddy bear")],
            'search_target': None
        }
        
        result = await robot_agent.search_mode_node(state)
        
        assert result['search_target'] == 'teddy bear'
        assert result['tool_results']['action'] == 'object_search'
        assert result['tool_results']['target'] == 'teddy bear'
        assert result['current_activity'] == 'searching'
    
    @pytest.mark.asyncio
    async def test_navigate_mode_node(self, robot_agent):
        """Test navigation mode functionality"""
        state = {
            'messages': [HumanMessage(content="Go to the kitchen")],
            'navigation_target': None
        }
        
        result = await robot_agent.navigate_mode_node(state)
        
        assert result['navigation_target'] == 'kitchen'
        assert result['tool_results']['action'] == 'navigate_to_location'
        assert result['tool_results']['destination'] == 'kitchen'
        assert result['current_activity'] == 'navigating'
    
    @pytest.mark.asyncio
    async def test_execute_action_node_object_search(self, robot_agent, mock_dependencies):
        """Test execution of object search action"""
        # Mock successful search
        mock_dependencies['search'].execute.return_value = {
            'found': True,
            'confidence': 0.85,
            'location': 'table'
        }
        
        state = {
            'tool_results': {
                'action': 'object_search',
                'target': 'keys'
            }
        }
        
        result = await robot_agent.execute_action_node(state)
        
        assert result['tool_results']['status'] == 'found'
        assert 'I found the keys!' in result['tool_results']['message']
        mock_dependencies['search'].execute.assert_called_once_with(
            object_name='keys',
            timeout=60,
            confidence_threshold=0.5
        )
    
    @pytest.mark.asyncio
    async def test_execute_action_node_navigation(self, robot_agent, mock_dependencies):
        """Test execution of navigation action"""
        state = {
            'tool_results': {
                'action': 'navigate_to_location',
                'destination': 'bedroom'
            }
        }
        
        result = await robot_agent.execute_action_node(state)
        
        assert result['tool_results']['status'] == 'arrived'
        mock_dependencies['movement'].turn.assert_called_once()
        mock_dependencies['movement'].move_forward.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_action_node_stop(self, robot_agent, mock_dependencies):
        """Test stop action execution"""
        state = {
            'tool_results': {
                'action': 'stop_movement'
            }
        }
        
        result = await robot_agent.execute_action_node(state)
        
        assert result['tool_results']['status'] == 'stopped'
        mock_dependencies['movement'].stop.assert_called_once()
    
    def test_route_by_intent(self, robot_agent):
        """Test intent routing logic"""
        # Test valid intents
        assert robot_agent.route_by_intent({'interaction_mode': 'search'}) == 'search'
        assert robot_agent.route_by_intent({'interaction_mode': 'navigate'}) == 'navigate'
        assert robot_agent.route_by_intent({'interaction_mode': 'play'}) == 'play'
        
        # Test invalid intent defaults to respond
        assert robot_agent.route_by_intent({'interaction_mode': 'invalid'}) == 'respond'
        assert robot_agent.route_by_intent({}) == 'respond'
    
    def test_should_continue(self, robot_agent):
        """Test conversation continuation logic"""
        # Test end conditions
        end_state = {
            'messages': [AIMessage(content="Goodbye!")],
            'current_activity': 'idle'
        }
        assert robot_agent.should_continue(end_state) == 'end'
        
        # Test continue condition
        continue_state = {
            'messages': [AIMessage(content="I'm searching!")],
            'current_activity': 'searching'
        }
        assert robot_agent.should_continue(continue_state) == 'continue'


class TestAgentIntegration:
    """Integration tests for the complete agent workflow"""
    
    @pytest.fixture
    def mock_full_system(self):
        """Mock the entire system for integration testing"""
        with patch('src.agent.langgraph_agent.ChatOpenAI') as mock_llm, \
             patch('src.agent.langgraph_agent.AnalyzeSceneTool') as mock_vision, \
             patch('src.agent.langgraph_agent.MovementController') as mock_movement, \
             patch('src.agent.langgraph_agent.Camera') as mock_camera, \
             patch('src.agent.langgraph_agent.ObjectSearchTool') as mock_search:
            
            # Setup realistic mock responses
            mock_llm_instance = Mock()
            mock_llm_instance.invoke = AsyncMock()
            mock_llm.return_value = mock_llm_instance
            
            mock_vision_instance = Mock()
            mock_vision_instance.execute = AsyncMock(return_value={
                'analysis': 'I see a child in a living room'
            })
            mock_vision.return_value = mock_vision_instance
            
            mock_movement_instance = Mock()
            mock_movement_instance.move_forward = AsyncMock(return_value={'status': 'success'})
            mock_movement_instance.turn = AsyncMock(return_value={'status': 'success'})
            mock_movement_instance.stop = AsyncMock(return_value={'status': 'success'})
            mock_movement.return_value = mock_movement_instance
            
            mock_search_instance = Mock()
            mock_search_instance.execute = AsyncMock(return_value={
                'found': True, 'confidence': 0.9
            })
            mock_search.return_value = mock_search_instance
            
            yield {
                'llm': mock_llm_instance,
                'vision': mock_vision_instance,
                'movement': mock_movement_instance,
                'search': mock_search_instance
            }
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(self, mock_full_system):
        """Test a complete object search workflow"""
        # Mock LLM to classify as search intent
        mock_response = Mock()
        mock_response.content = 'search'
        mock_full_system['llm'].invoke.return_value = mock_response
        
        robot = FamilyRobotGraph()
        
        # Run the complete workflow
        result = await robot.run("Find my keys", thread_id="test_search")
        
        # Verify the workflow executed
        assert result is not None
        assert 'messages' in result
        
        # Verify vision was called for perception
        mock_full_system['vision'].execute.assert_called()
        
        # Verify object search was executed
        mock_full_system['search'].execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_complete_navigation_workflow(self, mock_full_system):
        """Test a complete navigation workflow"""
        # Mock LLM to classify as navigate intent
        mock_response = Mock()
        mock_response.content = 'navigate'
        mock_full_system['llm'].invoke.return_value = mock_response
        
        robot = FamilyRobotGraph()
        
        # Run navigation workflow
        result = await robot.run("Go to the kitchen", thread_id="test_nav")
        
        # Verify movement was called
        mock_full_system['movement'].turn.assert_called()
        mock_full_system['movement'].move_forward.assert_called()


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_vision_failure_handling(self):
        """Test handling of vision analysis failures"""
        with patch('src.agent.langgraph_agent.AnalyzeSceneTool') as mock_vision:
            mock_vision_instance = Mock()
            mock_vision_instance.execute = AsyncMock(side_effect=Exception("Camera error"))
            mock_vision.return_value = mock_vision_instance
            
            robot = FamilyRobotGraph()
            
            state = {'messages': [], 'hardware_status': {}}
            result = await robot.perceive_node(state)
            
            # Should handle error gracefully
            assert result['last_vision'] == "Unable to analyze scene"
    
    @pytest.mark.asyncio
    async def test_movement_failure_handling(self):
        """Test handling of movement failures"""
        with patch('src.agent.langgraph_agent.MovementController') as mock_movement:
            mock_movement_instance = Mock()
            mock_movement_instance.move_forward = AsyncMock(side_effect=Exception("Motor error"))
            mock_movement.return_value = mock_movement_instance
            
            robot = FamilyRobotGraph()
            
            state = {
                'tool_results': {
                    'action': 'navigate_to_location',
                    'destination': 'kitchen'
                }
            }
            
            result = await robot.execute_action_node(state)
            
            # Should handle error and set error status
            assert result['tool_results']['status'] == 'error'
            assert 'error' in result['tool_results']
    
    def test_invalid_message_handling(self):
        """Test handling of invalid or empty messages"""
        robot = FamilyRobotGraph()
        
        # Test with empty state
        state = {}
        result = robot.route_by_intent(state)
        assert result == 'respond'
        
        # Test with None interaction_mode
        state = {'interaction_mode': None}
        result = robot.route_by_intent(state)
        assert result == 'respond'


# Test fixtures and utilities
@pytest.fixture
def sample_agent_state():
    """Provide a sample agent state for testing"""
    return {
        'messages': [HumanMessage(content="Hello robot!")],
        'current_user': 'child',
        'current_activity': 'idle',
        'emotion_state': 'happy',
        'interaction_mode': 'respond',
        'tool_results': {},
        'last_vision': 'A child in a room',
        'search_target': None,
        'navigation_target': None,
        'hardware_status': {'camera': 'active', 'movement': 'ready'}
    }


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])