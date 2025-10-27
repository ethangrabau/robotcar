Project Goal: Create a Home-Aware Agentic Robot
The objective is to evolve the PiCar-X from a robot that executes pre-defined scripts into a truly agentic system. This new system will be able to reason about its goals, create multi-step plans, and adapt to its environment to complete complex tasks like "find my backpack."

We will achieve this by migrating from our current approach of using large, all-in-one scripts to a more flexible "reasoning loop" that intelligently uses a "toolbox" of simpler, more fundamental skills.

Implementation & Deployment Plan
This plan is broken into distinct phases. Complete all steps in a phase, including the "Deploy & Test" checkpoint, before moving to the next. This ensures we have a stable, working robot at every stage.

Phase 1: Refactor to a Tool-Based Architecture
Goal: Reorganize the existing, working code into a modular structure. At the end of this phase, the robot will have the same core capabilities as before, but its code will be clean, scalable, and ready for agentic logic.

Conceptual Rationale: We are not adding new features yet. We are rebuilding the foundation. Instead of one large script (gpt_car.py) that does everything, we are creating a set of reliable, independent "primitive" classes for hardware control and a "Tool" for the agent to use.
Code: Hardware Primitives (hardware_interface.py)

In a src/ directory, create src/movement/hardware_interface.py.
Create a PicarxController class within it.
Migrate the core hardware methods from picarx/picarx.py into this class. It should have simple, direct methods:
move_forward(speed)
turn(angle)
stop()
set_camera_angle(pan, tilt)
get_distance() (using the ultrasonic sensor logic from 4.avoiding_obstacles.py)
Code: Vision Primitives (camera.py)

Create src/vision/camera.py.
Create a Camera class.
Add a method capture_image(filepath) that contains the logic to initialize the camera and save a single frame, using the vilib library as seen in your examples.

Deploy & Test: Primitives Validation

Action: Create a test script scripts/test_primitives.py. This script will import PicarxController and Camera and call each function individually (e.g., move forward for 1 second, turn 30 degrees, take one picture).
Deploy: Copy the new src and scripts directories to the robot.
Test: Run sudo python3 scripts/test_primitives.py on the Pi.
Verify: The robot moves correctly, and an image is saved. Do not proceed until these primitives are reliable.
Code: Create the First Agent Tool (vision_tools.py)

Create a new directory src/agent/tools/.
Inside, create vision_tools.py.
Define a class AnalyzeSceneTool. Its execute method will take a query string. It will:
Use the Camera class to capture an image.
Use the image analysis logic from gpt_examples/openai_helper.py to send the image and the query to the vision model.
Return the model's textual response.
Deploy & Test: The "What Do You See?" Agent Test

Action: Create a new main script, src/main_agent.py, that contains a simple loop:
It prompts for keyboard input ("What should I look for?").
It calls your new AnalyzeSceneTool with the input as the query.
It prints the text result to the console.
Deploy: Sync the updated src directory.
Test: Place a distinct object (like a red ball) in front of the robot. Run sudo python3 src/main_agent.py and type a red ball.
Verify: The robot should successfully capture an image, send it for analysis, and print a confirmation like: "Yes, I see a red ball on the floor." This confirms your entire new architecture works for a single, powerful tool.
Phase 2: Multi-Step Reasoning & Exploration
Goal: Upgrade the agent from executing single commands to creating and following a simple plan.

Conceptual Rationale: This is where true agentic behavior begins. Instead of just answering a single question, the agent will now take a goal, and if the first action doesn't achieve it, it will "think" again and decide on a second, different action.
Code: Enhance the Reasoning Loop (main_agent.py)

Modify the main loop to be stateful. It needs to remember the overall goal (e.g., "find the backpack") and the history of actions taken.
The prompt sent to the LLM should now include this context: "My goal is to [GOAL]. So far, I have done [ACTION 1] and the result was [RESULT 1]. What tool should I use next?"
Code: Create an ExploreTool

In src/agent/tools/movement_tools.py, create an ExploreTool.
This tool will execute a simple, predefined search pattern, like turning in a slow 360-degree circle while periodically calling AnalyzeSceneTool to create a summary of its surroundings.
Deploy & Test: The "Find the Backpack" Test (Single Room)

Deploy: Sync the updated src directory.
Test: Place a backpack in the same room, but out of the robot's initial view. Run sudo python3 src/main_agent.py and give the command find the backpack.
Verify: Observe the agent's logic printed to the console.
Step 1: It should call AnalyzeSceneTool. The result will be "backpack not found."
Step 2: It should reason that since the object isn't visible, it must explore. It should then call the ExploreTool.
Step 3: During exploration, it should see the backpack and report, "I have found the backpack."
Phase 3: Environmental Awareness (Obstacles & Doors)
Goal: Give the agent the tools to understand and navigate a real-world, cluttered environment.

Conceptual Rationale: The robot learns that the world isn't an empty arena. It must check for obstacles before moving and can find exits to move between rooms. This makes its navigation far more robust.
Code: Create Environmental Tools

In src/agent/tools/navigation_tools.py, create two new tools:
CheckForObstaclesTool: Uses the get_distance() primitive. Returns {"obstacle": true, "distance": X} or {"obstacle": false}.
FindDoorTool: Uses the AnalyzeSceneTool with the specific query: "Is there an open door or exit in view? Respond only with its location ('left', 'center', 'right') or 'none'."
Code: Integrate Checks into the Reasoning Loop

Modify the agent's core prompt. Add a rule: "Before you decide to use any movement tool, you must first use the CheckForObstaclesTool."
If an obstacle is detected, the agent's next decision should be to turn away from it.
Add another rule: "If you have explored a room and cannot find the target object, your next goal is to use the FindDoorTool."
Deploy & Test: The Obstacle Course & Escape Room

Deploy: Sync your final src directory.
Test 1 (Obstacle): Place a box in front of the robot. Command find the backpack (with the backpack visible behind the box).
Verify 1: The robot should see the obstacle, turn to avoid it, and then proceed toward the backpack.
Test 2 (Escape): Place the robot in a room without the backpack. Command find the backpack.
Verify 2: The robot should explore, fail to find the object, announce it's looking for a door, find the door, and drive through it.