"""Configuration settings for the robot assistant."""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Hardware settings
DEFAULT_HEAD_TILT = 20  # Default camera tilt angle
DEFAULT_POWER = 30  # Default motor power (0-100)

# Voice settings
TTS_VOICE = os.getenv('TTS_VOICE', 'echo')
STT_LANGUAGE = os.getenv('STT_LANGUAGE', 'en-US')

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

# Safety settings
SAFE_DISTANCE = 40  # cm
DANGER_DISTANCE = 20  # cm
MAX_SEARCH_TIME = 120  # seconds

# File paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'

# Create necessary directories
for directory in [DATA_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True)
