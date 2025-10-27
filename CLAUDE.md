# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Testing
- **Run all tests**: `make test` or `./run_tests.sh`
- **Unit tests only**: `make test-unit` or `python -m pytest tests/unit/ -v`
- **Integration tests**: `make test-integration` or `python -m pytest tests/integration/ -v`
- **E2E tests**: `make test-e2e` or `python -m pytest tests/e2e/ -v`
- **Run specific test file**: `python -m pytest tests/unit/test_voice.py -v`
- **Run with coverage**: `python -m pytest tests/unit/ --cov=src --cov-report=term-missing`

### Code Quality
- **Lint code**: `make lint` (runs flake8 and mypy)
- **Format code**: `make format` (uses black)
- **Check formatting**: `make check-format`
- **Clean build artifacts**: `make clean`

### Development
- **Install dependencies**: `pip install -r requirements.txt`
- **Install dev dependencies**: `make install-dev`
- **Run main application**: `python -m src.main`
- **Run agent system**: `python -m src.main_agent`

### Deployment to Raspberry Pi
- **Deploy code**: Use `scripts/deploy_and_test.sh` (configured for Pi at 192.168.0.151)
- **SSH to Pi**: `ssh pi@192.168.0.151` (password: raspberry)
- **Run on Pi**: `cd /home/pi/Robot_Car && python -m src.main_agent`

## Architecture Overview

This is a family-friendly robot assistant built on the PiCar-X platform with Raspberry Pi, implementing an embodied AI system with cloud augmentation.

### Core Components

1. **Agent System** (`src/agent/`)
   - **Main Agent**: `src/main_agent.py` - Entry point for the agent system
   - **Tool-Based Architecture**: Agents use tools for specific capabilities
   - **Vision Tools**: `tools/vision_tools.py` - Scene analysis using GPT-4V
   - **Object Search**: `tools/object_search_tool.py` - Find and approach objects
   - **Movement Tools**: `tools/movement_tools.py` - Robot navigation primitives

2. **Hardware Abstraction** (`src/movement/`, `src/vision/`, `src/voice/`)
   - **Movement**: PiCar-X control through robot-hat library
   - **Vision**: Camera interface using picamera2/OpenCV
   - **Voice**: Speech recognition (Whisper) and TTS (gTTS)

3. **Smart Home Integration** (`src/home_control/`)
   - Google Cast integration for TV control
   - Future: Google Assistant SDK for broader home control

4. **Memory System** (`src/memory/`)
   - Context management for conversations
   - Family member profiles and preferences

### Tool Registry Pattern

The system uses a tool registry pattern where high-level agents can invoke specific tools:
- **High-Level Tools**: Complex tasks (object search, room navigation)
- **Mid-Level Tools**: Navigation primitives (go to room, avoid obstacles)
- **Low-Level Tools**: Direct hardware control (move forward, turn, camera control)

### Key Design Principles

1. **Modular Architecture**: Each component has a single responsibility
2. **Async/Await Pattern**: Used for I/O operations and tool execution
3. **Error Recovery**: All hardware operations include error handling
4. **Safety First**: Movement commands include obstacle detection and safety checks
5. **Privacy Protection**: Face recognition done locally, never sent to cloud

### API Keys and Configuration

- **Required**: `OPENAI_API_KEY` environment variable for GPT-4V vision analysis
- **Optional**: Google Cloud credentials for enhanced TTS
- Configuration stored in `src/config.py` and `.env` files

### Hardware Dependencies

- **PiCar-X**: Physical robot platform
- **robot-hat**: Hardware interface library
- **vilib**: Vision processing library
- **picamera2**: Camera interface
- **RPi.GPIO**: GPIO control

### Testing Strategy

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete user workflows
- **Hardware Tests**: `scripts/test_hardware.py` for robot validation

### Common Development Tasks

When modifying vision capabilities:
1. Check `src/vision/camera.py` for camera interface
2. Update tools in `src/agent/tools/vision_tools.py`
3. Test with `scripts/test_camera.py`

When adding new agent capabilities:
1. Create tool in `src/agent/tools/`
2. Inherit from `BaseTool` class
3. Register in agent's tool registry
4. Add tests in `tests/unit/`

When deploying to Pi:
1. Ensure code works locally first
2. Use `scripts/deploy_and_test.sh` for quick deployment
3. Monitor logs via SSH for debugging