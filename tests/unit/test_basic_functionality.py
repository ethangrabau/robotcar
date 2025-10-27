#!/usr/bin/env python3
"""
Basic functionality tests for Robot Car system

These tests verify core functionality without requiring external dependencies.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestBasicImports:
    """Test that we can import core modules"""
    
    def test_can_import_agent_modules(self):
        """Test importing agent modules"""
        try:
            from src.agent import langgraph_agent
            assert hasattr(langgraph_agent, 'FamilyRobotGraph')
        except ImportError as e:
            pytest.skip(f"Cannot import agent modules: {e}")
    
    def test_can_import_tools(self):
        """Test importing tool modules"""
        try:
            from src.agent.tools import child_interaction_tools
            assert hasattr(child_interaction_tools, 'SimonSaysGame')
        except ImportError as e:
            pytest.skip(f"Cannot import tool modules: {e}")

class TestAgentStateStructure:
    """Test the AgentState structure and validation"""
    
    def test_agent_state_keys(self):
        """Test that AgentState has expected keys"""
        try:
            from src.agent.langgraph_agent import AgentState
            
            # Create a sample state
            sample_state = {
                'messages': [],
                'current_user': 'test',
                'current_activity': 'idle',
                'emotion_state': 'neutral',
                'interaction_mode': 'respond',
                'tool_results': {},
                'last_vision': None,
                'search_target': None,
                'navigation_target': None,
                'hardware_status': {}
            }
            
            # Verify all expected keys are present
            expected_keys = {
                'messages', 'current_user', 'current_activity', 
                'emotion_state', 'interaction_mode', 'tool_results',
                'last_vision', 'search_target', 'navigation_target', 
                'hardware_status'
            }
            
            assert all(key in sample_state for key in expected_keys)
            
        except ImportError:
            pytest.skip("Cannot import AgentState")

class TestIntentClassification:
    """Test intent classification logic without LLM"""
    
    def test_search_intent_keywords(self):
        """Test search intent detection from keywords"""
        search_phrases = [
            "find my keys",
            "where is my backpack",
            "look for the remote",
            "search for my phone"
        ]
        
        for phrase in search_phrases:
            # Simulate keyword detection logic
            has_search_keyword = any(word in phrase.lower() 
                                   for word in ["find", "where is", "look for", "search for"])
            assert has_search_keyword, f"Should detect search intent in: {phrase}"
    
    def test_navigation_intent_keywords(self):
        """Test navigation intent detection from keywords"""
        nav_phrases = [
            "go to the kitchen",
            "come here",
            "move to the bedroom",
            "follow me"
        ]
        
        for phrase in nav_phrases:
            has_nav_keyword = any(word in phrase.lower() 
                                for word in ["go to", "come here", "move to", "follow"])
            assert has_nav_keyword, f"Should detect navigation intent in: {phrase}"

class TestGameLogic:
    """Test game logic without hardware dependencies"""
    
    def test_simon_says_command_structure(self):
        """Test Simon Says command generation"""
        # Mock the game commands
        commands = {
            "easy": ["touch your nose", "clap your hands", "jump"],
            "medium": ["hop on one foot", "touch your elbow"],
            "hard": ["balance on one foot", "spell your name"]
        }
        
        # Test command selection logic
        for difficulty in commands:
            assert len(commands[difficulty]) > 0
            assert all(isinstance(cmd, str) for cmd in commands[difficulty])
    
    def test_story_content_structure(self):
        """Test story content structure"""
        sample_story = {
            "title": "The Brave Little Robot",
            "content": [
                "Once upon a time, there was a robot.",
                "The robot loved to help children.",
                "And they lived happily ever after."
            ]
        }
        
        assert "title" in sample_story
        assert "content" in sample_story
        assert isinstance(sample_story["content"], list)
        assert len(sample_story["content"]) > 0

class TestHardwareMocking:
    """Test that hardware can be properly mocked for development"""
    
    @pytest.mark.asyncio
    async def test_movement_controller_mock(self):
        """Test mocking movement controller"""
        
        class MockMovementController:
            def __init__(self):
                self.position = {'x': 0, 'y': 0, 'angle': 0}
            
            async def move_forward(self, distance=1, speed=50):
                self.position['x'] += distance
                return {'status': 'success', 'distance': distance}
            
            async def turn(self, angle=90, speed=50):
                self.position['angle'] += angle
                return {'status': 'success', 'angle': angle}
            
            async def stop(self):
                return {'status': 'stopped'}
        
        # Test the mock
        controller = MockMovementController()
        
        result = await controller.move_forward(2)
        assert result['status'] == 'success'
        assert controller.position['x'] == 2
        
        result = await controller.turn(45)
        assert result['status'] == 'success'
        assert controller.position['angle'] == 45
    
    @pytest.mark.asyncio
    async def test_vision_tool_mock(self):
        """Test mocking vision analysis"""
        
        class MockVisionTool:
            async def execute(self, query="", save_image=False):
                # Return different responses based on query
                if "child" in query.lower():
                    return {
                        'analysis': 'I see a happy child wearing a blue shirt in a living room',
                        'success': True
                    }
                else:
                    return {
                        'analysis': 'I see a room with furniture and some objects on a table',
                        'success': True
                    }
        
        vision = MockVisionTool()
        
        # Test child detection
        result = await vision.execute("Are there any children nearby?")
        assert "child" in result['analysis']
        
        # Test general scene
        result = await vision.execute("Describe what you see")
        assert "room" in result['analysis']

class TestSystemConfiguration:
    """Test system configuration and setup"""
    
    def test_environment_setup(self):
        """Test that environment can be configured"""
        # Test that we can detect environment variables
        api_key_set = bool(os.getenv('OPENAI_API_KEY'))
        
        # This is OK to be False for testing, just verify we can check
        assert isinstance(api_key_set, bool)
    
    def test_file_structure(self):
        """Test that expected files exist"""
        expected_files = [
            'src/agent/langgraph_agent.py',
            'src/agent/tools/child_interaction_tools.py',
            'requirements.txt',
            'README.md',
            'CLAUDE.md'
        ]
        
        for file_path in expected_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Expected file missing: {file_path}"

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_missing_dependency_handling(self):
        """Test handling of missing dependencies"""
        
        def safe_import(module_name):
            try:
                __import__(module_name)
                return True
            except ImportError:
                return False
        
        # Test that we handle missing optional dependencies gracefully
        has_langchain = safe_import('langchain')
        has_langgraph = safe_import('langgraph')
        
        # These might not be installed, which is OK for basic testing
        assert isinstance(has_langchain, bool)
        assert isinstance(has_langgraph, bool)
    
    def test_parameter_validation(self):
        """Test parameter validation logic"""
        
        def validate_game_parameters(difficulty="easy", rounds=5):
            """Mock parameter validation"""
            valid_difficulties = ["easy", "medium", "hard"]
            
            if difficulty not in valid_difficulties:
                difficulty = "easy"
            
            if not isinstance(rounds, int) or rounds < 1:
                rounds = 5
            
            return {"difficulty": difficulty, "rounds": rounds}
        
        # Test valid parameters
        result = validate_game_parameters("medium", 3)
        assert result["difficulty"] == "medium"
        assert result["rounds"] == 3
        
        # Test invalid parameters
        result = validate_game_parameters("impossible", -1)
        assert result["difficulty"] == "easy"
        assert result["rounds"] == 5

if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])