#!/usr/bin/env python3
"""
Unit tests for Child Interaction Tools

Tests all the game and educational tools designed for child interactions.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.tools.child_interaction_tools import (
    SimonSaysGame,
    HideAndSeekGame,
    StorytellingTool,
    EducationalGameTool,
    SafetyConfig
)

class TestSafetyConfig:
    """Test the SafetyConfig dataclass"""
    
    def test_default_values(self):
        """Test default safety configuration values"""
        config = SafetyConfig()
        
        assert config.min_distance == 1.5
        assert config.max_speed == 0.3
        assert config.volume_limit == 60
        assert config.interaction_timeout == 300
        assert config.require_parent_presence == False


class TestSimonSaysGame:
    """Test the Simon Says game tool"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all hardware dependencies"""
        with patch('src.agent.tools.child_interaction_tools.MovementController') as mock_movement, \
             patch('src.agent.tools.child_interaction_tools.TextToSpeech') as mock_tts, \
             patch('src.agent.tools.child_interaction_tools.Camera') as mock_camera:
            
            mock_movement_instance = Mock()
            mock_movement.return_value = mock_movement_instance
            
            mock_tts_instance = Mock()
            mock_tts_instance.speak = AsyncMock()
            mock_tts.return_value = mock_tts_instance
            
            mock_camera_instance = Mock()
            mock_camera.return_value = mock_camera_instance
            
            yield {
                'movement': mock_movement_instance,
                'tts': mock_tts_instance,
                'camera': mock_camera_instance
            }
    
    @pytest.fixture
    def simon_game(self, mock_dependencies):
        """Create SimonSaysGame instance with mocked dependencies"""
        return SimonSaysGame()
    
    def test_initialization(self, simon_game):
        """Test SimonSaysGame initializes correctly"""
        assert simon_game.name == "simon_says_game"
        assert simon_game.description == "Play Simon Says with children - safe, fun movement game"
        assert simon_game.commands is not None
        assert 'easy' in simon_game.commands
        assert 'medium' in simon_game.commands
        assert 'hard' in simon_game.commands
    
    def test_commands_structure(self, simon_game):
        """Test that commands are properly structured"""
        # Check easy commands
        easy_commands = simon_game.commands['easy']
        assert len(easy_commands) > 0
        assert 'touch your nose' in easy_commands
        assert 'clap your hands' in easy_commands
        
        # Check medium commands
        medium_commands = simon_game.commands['medium']
        assert len(medium_commands) > 0
        assert any('hop' in cmd for cmd in medium_commands)
        
        # Check hard commands
        hard_commands = simon_game.commands['hard']
        assert len(hard_commands) > 0
        assert any('balance' in cmd for cmd in hard_commands)
    
    @pytest.mark.asyncio
    async def test_execute_easy_game(self, simon_game, mock_dependencies):
        """Test executing an easy difficulty game"""
        with patch.object(simon_game, '_ensure_safe_environment', new_callable=AsyncMock), \
             patch.object(simon_game, '_check_action_compliance', new_callable=AsyncMock, return_value=True):
            
            result = await simon_game.execute(difficulty="easy", rounds=2)
            
            assert result['success'] == True
            assert result['game'] == "Simon Says"
            assert result['score'] >= 0
            assert result['rounds'] == 2
            assert result['difficulty'] == "easy"
            assert len(result['commands_given']) == 2
            
            # Verify TTS was called multiple times
            assert mock_dependencies['tts'].speak.call_count >= 3  # Intro + commands + end
    
    @pytest.mark.asyncio
    async def test_execute_medium_game(self, simon_game, mock_dependencies):
        """Test executing a medium difficulty game"""
        with patch.object(simon_game, '_ensure_safe_environment', new_callable=AsyncMock), \
             patch.object(simon_game, '_check_action_compliance', new_callable=AsyncMock, return_value=False):
            
            result = await simon_game.execute(difficulty="medium", rounds=3)
            
            assert result['difficulty'] == "medium"
            assert result['rounds'] == 3
            # Score should be 0 since we mocked compliance as False
            assert result['score'] == 0
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, simon_game):
        """Test parameter validation"""
        with patch.object(simon_game, '_ensure_safe_environment', new_callable=AsyncMock), \
             patch.object(simon_game, '_check_action_compliance', new_callable=AsyncMock, return_value=True):
            
            # Test default parameters
            result = await simon_game.execute()
            assert result['difficulty'] == "easy"
            assert result['rounds'] == 5
            
            # Test invalid difficulty defaults to easy
            result = await simon_game.execute(difficulty="impossible")
            assert result['difficulty'] == "impossible"  # Tool accepts but uses what's provided


class TestHideAndSeekGame:
    """Test the Hide and Seek game tool"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock hardware dependencies for hide and seek"""
        with patch('src.agent.tools.child_interaction_tools.MovementController') as mock_movement, \
             patch('src.agent.tools.child_interaction_tools.TextToSpeech') as mock_tts, \
             patch('src.agent.tools.child_interaction_tools.Camera') as mock_camera:
            
            mock_movement_instance = Mock()
            mock_movement_instance.servo_control = AsyncMock()
            mock_movement_instance.turn = AsyncMock()
            mock_movement.return_value = mock_movement_instance
            
            mock_tts_instance = Mock()
            mock_tts_instance.speak = AsyncMock()
            mock_tts.return_value = mock_tts_instance
            
            mock_camera_instance = Mock()
            mock_camera.return_value = mock_camera_instance
            
            yield {
                'movement': mock_movement_instance,
                'tts': mock_tts_instance,
                'camera': mock_camera_instance
            }
    
    @pytest.fixture
    def hide_seek_game(self, mock_dependencies):
        """Create HideAndSeekGame instance"""
        return HideAndSeekGame()
    
    def test_initialization(self, hide_seek_game):
        """Test HideAndSeekGame initializes correctly"""
        assert hide_seek_game.name == "hide_and_seek"
        assert hide_seek_game.description == "Play hide and seek - robot counts and searches safely"
    
    @pytest.mark.asyncio
    async def test_execute_game(self, hide_seek_game, mock_dependencies):
        """Test executing a hide and seek game"""
        with patch.object(hide_seek_game, '_look_for_children', new_callable=AsyncMock, return_value=True):
            
            result = await hide_seek_game.execute(count_time=5, search_time=10)
            
            assert result['success'] == True
            assert result['game'] == "Hide and Seek"
            assert result['found_count'] >= 0
            assert result['search_duration'] <= 10
            
            # Verify camera movements
            mock_dependencies['movement'].servo_control.assert_called()
            
            # Verify TTS announcements
            assert mock_dependencies['tts'].speak.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_no_children_found(self, hide_seek_game, mock_dependencies):
        """Test game when no children are found"""
        with patch.object(hide_seek_game, '_look_for_children', new_callable=AsyncMock, return_value=False):
            
            result = await hide_seek_game.execute(count_time=2, search_time=5)
            
            assert result['found_count'] == 0
            assert "champion" in result  # Should congratulate child


class TestStorytellingTool:
    """Test the Storytelling tool"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock TTS for storytelling"""
        with patch('src.agent.tools.child_interaction_tools.TextToSpeech') as mock_tts:
            mock_tts_instance = Mock()
            mock_tts_instance.speak = AsyncMock()
            mock_tts.return_value = mock_tts_instance
            
            yield {'tts': mock_tts_instance}
    
    @pytest.fixture
    def storyteller(self, mock_dependencies):
        """Create StorytellingTool instance"""
        return StorytellingTool()
    
    def test_initialization(self, storyteller):
        """Test StorytellingTool initializes correctly"""
        assert storyteller.name == "storytelling"
        assert storyteller.description == "Tell stories or create them together with children"
        assert storyteller.stories is not None
        assert 'adventure' in storyteller.stories
        assert 'friendship' in storyteller.stories
    
    def test_story_content(self, storyteller):
        """Test that stories have proper content"""
        adventure_stories = storyteller.stories['adventure']
        assert len(adventure_stories) > 0
        
        story = adventure_stories[0]
        assert 'title' in story
        assert 'content' in story
        assert len(story['content']) > 0
        assert isinstance(story['content'], list)
    
    @pytest.mark.asyncio
    async def test_premade_story(self, storyteller, mock_dependencies):
        """Test telling a premade story"""
        result = await storyteller.execute(story_type="premade", theme="adventure")
        
        assert result['success'] == True
        assert result['story_type'] == "premade"
        assert result['theme'] == "adventure"
        assert 'story_title' in result
        
        # Verify TTS was called for each story line
        assert mock_dependencies['tts'].speak.call_count > 5
    
    @pytest.mark.asyncio
    async def test_collaborative_story(self, storyteller, mock_dependencies):
        """Test starting a collaborative story"""
        result = await storyteller.execute(story_type="collaborative", theme="friendship")
        
        assert result['success'] == True
        assert result['story_type'] == "collaborative"
        assert result['prompt_given'] == True
        
        # Should have given initial prompt
        assert mock_dependencies['tts'].speak.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_unknown_story_type(self, storyteller):
        """Test handling unknown story type"""
        result = await storyteller.execute(story_type="unknown", theme="adventure")
        
        assert result['success'] == True
        assert result['story_type'] == "unknown"


class TestEducationalGameTool:
    """Test the Educational Game tool"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for educational games"""
        with patch('src.agent.tools.child_interaction_tools.TextToSpeech') as mock_tts, \
             patch('src.agent.tools.child_interaction_tools.Camera') as mock_camera:
            
            mock_tts_instance = Mock()
            mock_tts_instance.speak = AsyncMock()
            mock_tts.return_value = mock_tts_instance
            
            mock_camera_instance = Mock()
            mock_camera.return_value = mock_camera_instance
            
            yield {
                'tts': mock_tts_instance,
                'camera': mock_camera_instance
            }
    
    @pytest.fixture
    def edu_game(self, mock_dependencies):
        """Create EducationalGameTool instance"""
        return EducationalGameTool()
    
    def test_initialization(self, edu_game):
        """Test EducationalGameTool initializes correctly"""
        assert edu_game.name == "educational_game"
        assert edu_game.description == "Play educational games - counting, colors, shapes, letters"
        assert edu_game.content is not None
        assert 'counting' in edu_game.content
        assert 'colors' in edu_game.content
    
    def test_content_structure(self, edu_game):
        """Test educational content structure"""
        counting_content = edu_game.content['counting']
        assert 'beginner' in counting_content
        assert 'intermediate' in counting_content
        assert 'advanced' in counting_content
        
        # Check beginner counting structure
        beginner = counting_content['beginner']
        assert 'range' in beginner
        assert 'problems' in beginner
        assert beginner['range'] == (1, 10)
        
        colors_content = edu_game.content['colors']
        assert 'beginner' in colors_content
        assert len(colors_content['beginner']) >= 4  # Basic colors
    
    @pytest.mark.asyncio
    async def test_counting_game_beginner(self, edu_game, mock_dependencies):
        """Test beginner counting game"""
        result = await edu_game.execute(subject="counting", difficulty="beginner")
        
        assert result['success'] == True
        assert result['game'] == "counting"
        assert result['difficulty'] == "beginner"
        assert 'range_practiced' in result
        
        # Verify TTS was used for counting
        assert mock_dependencies['tts'].speak.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_colors_game(self, edu_game, mock_dependencies):
        """Test colors learning game"""
        result = await edu_game.execute(subject="colors", difficulty="beginner")
        
        assert result['success'] == True
        assert result['game'] == "colors"
        assert result['difficulty'] == "beginner"
        assert 'color_learned' in result
        
        # Verify a valid color was chosen
        valid_colors = edu_game.content['colors']['beginner']
        assert result['color_learned'] in valid_colors
    
    @pytest.mark.asyncio
    async def test_unknown_subject(self, edu_game):
        """Test handling unknown subject"""
        result = await edu_game.execute(subject="unknown", difficulty="beginner")
        
        assert result['success'] == True
        assert result['subject'] == "unknown"
        assert result['difficulty'] == "beginner"
    
    @pytest.mark.asyncio
    async def test_default_parameters(self, edu_game, mock_dependencies):
        """Test default parameters"""
        result = await edu_game.execute()
        
        assert result['subject'] == "counting"  # Should default to counting
        assert result['difficulty'] == "beginner"  # Should default to beginner


class TestToolParameterValidation:
    """Test parameter validation across all tools"""
    
    @pytest.mark.asyncio
    async def test_simon_says_parameters(self):
        """Test SimonSaysGame parameter validation"""
        with patch('src.agent.tools.child_interaction_tools.MovementController'), \
             patch('src.agent.tools.child_interaction_tools.TextToSpeech'), \
             patch('src.agent.tools.child_interaction_tools.Camera'):
            
            game = SimonSaysGame()
            
            # Test parameter requirements
            assert "difficulty" in game.parameters
            assert "rounds" in game.parameters
            
            # Test parameter defaults
            assert game.parameters["difficulty"]["default"] == "easy"
            assert game.parameters["rounds"]["default"] == 5
    
    @pytest.mark.asyncio
    async def test_hide_seek_parameters(self):
        """Test HideAndSeekGame parameter validation"""
        with patch('src.agent.tools.child_interaction_tools.MovementController'), \
             patch('src.agent.tools.child_interaction_tools.TextToSpeech'), \
             patch('src.agent.tools.child_interaction_tools.Camera'):
            
            game = HideAndSeekGame()
            
            assert "count_time" in game.parameters
            assert "search_time" in game.parameters
            assert game.parameters["count_time"]["default"] == 20
    
    def test_storytelling_parameters(self):
        """Test StorytellingTool parameter validation"""
        with patch('src.agent.tools.child_interaction_tools.TextToSpeech'):
            tool = StorytellingTool()
            
            assert "story_type" in tool.parameters
            assert "theme" in tool.parameters
            assert tool.parameters["story_type"]["default"] == "premade"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])