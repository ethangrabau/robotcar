"""
Pytest configuration and fixtures for testing the robot.
"""
import pytest
from unittest.mock import MagicMock, patch
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Fixtures
@pytest.fixture
def mock_robot_controller():
    """Create a mock RobotController for testing."""
    with patch('src.movement.navigation.RobotController') as mock:
        yield mock()

@pytest.fixture
def mock_speech_recognizer():
    """Create a mock SpeechRecognizer for testing."""
    with patch('src.voice.speech_recognition.SpeechRecognizer') as mock:
        yield mock()

@pytest.fixture
def mock_text_to_speech():
    """Create a mock TextToSpeech for testing."""
    with patch('src.voice.text_to_speech.TextToSpeech') as mock:
        yield mock()

@pytest.fixture
def test_audio_file(tmp_path):
    """Create a test audio file."""
    test_file = tmp_path / "test_audio.wav"
    test_file.write_bytes(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
    return str(test_file)
