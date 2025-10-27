# PiCar-X Object Search Tool

This tool integrates the enhanced object search functionality into the agent architecture. It enables the robot to search for objects using GPT-4 Vision, move toward detected objects, and provide detailed feedback.

## Setup Instructions

1. **Deploy the code to the Pi**
   - All necessary files have been copied to the `~/family-robot/` directory on the Pi

2. **Configure the OpenAI API Key**
   - Connect to the Pi via SSH
   - Run the setup script with your API key:
     ```bash
     cd ~/family-robot
     chmod +x setup_api_key.sh
     ./setup_api_key.sh YOUR_OPENAI_API_KEY
     ```

3. **Enable the Speaker Switch (if needed for audio feedback)**
   ```bash
   pinctrl set 20 op dh
   ```

## Running the Object Search Tool

Run the test script to search for objects:

```bash
cd ~/family-robot
python3 test_object_search_tool.py --object "tennis ball" --timeout 60 --confidence 0.6
```

### Command-line Arguments

- `--object`: The object to search for (default: "tennis ball")
- `--timeout`: Search timeout in seconds (default: 60)
- `--confidence`: Confidence threshold (0.0-1.0) (default: 0.5)
- `--area`: Area to search in (optional)

## Features

The integrated object search tool includes:

1. **Enhanced Vision Detection**
   - Uses GPT-4o Vision API for accurate object detection
   - Provides position information (left/right/center, top/bottom/middle)
   - Filters results by confidence threshold

2. **Improved Search Patterns**
   - Performs initial 360-degree scan in place
   - Uses adaptive exploration pattern with obstacle avoidance
   - Optimized turning angles based on detected object position

3. **Reliable Distance Sensing**
   - Takes multiple ultrasonic sensor readings
   - Filters out invalid readings
   - Averages valid readings for improved reliability

4. **Object Approach**
   - Turns toward detected objects based on position
   - Moves forward with distance checking
   - Stops at a safe distance from the object

## Integration with Agent Architecture

The object search tool is fully integrated with the agent architecture:

- Uses the `PiCarXHardware` class for hardware control
- Uses the `GPTVision` class for vision processing
- Implements async methods compatible with the agent system
- Returns structured results for agent processing

## Troubleshooting

- If the camera isn't working, check that the camera module is enabled in `raspi-config`
- If the ultrasonic sensor gives erratic readings, check the connections
- If the API calls fail, verify your API key is correctly set up
- Check the log file `object_search_test.log` for detailed error information
