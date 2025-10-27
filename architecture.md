# Embodied AI Family Assistant Robot: Architecture & Implementation Plan

## Project Overview

We are building a home-based, cloud-augmented, voice-interactive **AI assistant robot** for family use. This robot will:

* Navigate physically using a mobile base (SunFounder PiCar-X)
* Respond to voice commands using Whisper (OpenAI STT) and Google TTS
* Recognize family members by face
* Interface with smart home devices via Google Assistant SDK
* Maintain persistent, personalized memory (preferences, routines, etc.)
* Filter inappropriate content for child-friendly interactions

The system will run on a **Raspberry Pi 4/5** with Python-based orchestration, using modular architecture and cloud services for high performance and flexibility.

---

## Hardware Components

| Component        | Purpose                          |
| ---------------- | -------------------------------- |
| Raspberry Pi 4/5 | Compute and storage              |
| PiCar-X Base     | Physical mobility, camera, audio |
| Camera Module    | Vision (face recognition)        |
| Mic + Speaker    | Voice input/output               |
| Robot HAT        | Interface with sensors/motors    |
| Optional: Coral  | Vision acceleration (if needed)  |

---

## Python Coding Best Practices

* **Use virtual environments**: isolate dependencies via `venv`
* **Use `requirements.txt`**: manage all dependencies
* **Structure code modularly**: separate features by functionality
* **Use logging and error handling**: never fail silently
* **Use `.env` for API keys**: keep secrets out of code
* **Write pseudocode first**: design before implementing
* **Document functions**: use docstrings and comments

---

## Deployment Plan (via SSH)

1. **Initial Setup**:

   * Flash Raspberry Pi OS
   * Enable SSH + WiFi config via `boot` partition
2. **Remote Access**:

   ```bash
   ssh pi@<robot_ip_address>
   ```
3. **Install requirements**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run main program**:

   ```bash
   python main.py
   ```
5. **Automate startup (optional)**:

   * Use `crontab` or systemd to run on boot

---

## Code Structure

```plaintext
main.py
├── voice/
│   ├── stt.py                # Whisper STT via OpenAI
│   ├── tts.py                # Google TTS output
│   ├── wakeword.py           # Porcupine wake-word detector
├── vision/
│   ├── recognize.py          # Face detection/recognition (local-only)
│   └── capture.py            # Frame grabbing
├── memory/
│   ├── profiles.json         # Family profiles
│   ├── context.py            # Recent conversation memory
│   └── memory_manager.py     # Profile + vector storage
├── home_control/
│   └── google_assistant.py   # Sends smart home commands
├── filtering/
│   ├── moderation.py         # OpenAI moderation API
│   └── safe_search.py        # Whitelisted content filtering
├── movement/
│   └── navigation.py         # Drive commands, room patrol
├── audio/
│   └── playback.py           # Audible integration
├── agentic/
│   ├── reasoning.py          # LLM-based decision making and tool use
│   └── tools.py              # Registry of available tools
├── config.py                 # Constants, API keys loader
└── utils.py                  # Shared helpers
```

---

## Hybrid Agent-Tool Architecture

### Core Design Principles
1. **Layered Tool Abstraction**: Tools are organized in layers from high-level tasks to low-level controls
2. **Agentic Flexibility**: LLM can choose the right tool for each situation
3. **State Persistence**: Complex operations maintain their own state when needed
4. **Progressive Disclosure**: Start with high-level tools, expose lower levels as needed

### Agent Loop

```python
PERCEIVE → REASON → ACT → LEARN
```

### Reasoning Overview

The robot uses OpenAI's function-calling API to let the LLM decide which tool to use based on user input. Context is gathered from memory, recent conversations, and current observations (e.g. recognized faces).

### Tool Registry Example (`tools.py`):

```python
TOOLS = {
    # High-Level Tools (Task-Oriented)
    "search_for_object": {
        "function": object_searcher.search,
        "description": "Search for an object in the environment",
        "parameters": {
            "object_name": "string",
            "search_area": "string",
            "timeout": "number"
        }
    },
    
    # Mid-Level Tools (Navigation)
    "navigate_to_room": {
        "function": navigator.go_to_room,
        "description": "Navigate to a specific room while avoiding obstacles",
        "parameters": {
            "room_name": "string"
        }
    },
    
    # Low-Level Controls (Direct Hardware)
    "move_forward": {
        "function": car.move_forward,
        "description": "Move forward a specific distance",
        "parameters": {
            "distance": "number",
            "speed": "number"
        }
    },
    "turn": {
        "function": car.turn,
        "description": "Rotate in place",
        "parameters": {
            "degrees": "number",
            "speed": "number"
        }
    },
    
    # Specialized Tools
    "analyze_scene": {
        "function": vision.analyze_scene,
        "description": "Analyze the current camera view",
        "parameters": {
            "query": "string"
        }
    }
}
```

### When to Use Each Level
1. **High-Level Tools**: Common tasks (search, navigation)
2. **Mid-Level Tools**: Complex but common operations
3. **Low-Level Tools**: Precise control or novel situations

### Reasoning Process
1. Parse user intent
2. Select appropriate tool level
3. Execute with appropriate parameters
4. Learn from results

### LLM Reasoning Flow (`reasoning.py`):

```python
def decide_action(transcript, memory):
    context = gather_context(memory)
    tools_metadata = get_tool_definitions()
    response = call_openai_with_tools(transcript, tools_metadata, context)
    return parse_function_call(response)
```

### Function Calling Format (OpenAI Assistant or direct API):

```json
{
  "name": "turn_on_light",
  "description": "Turn on a smart light using Google Assistant",
  "parameters": {
    "location": "string"
  }
}
```

### Best Practices for Agentic Systems:

* Register tools with names + descriptions
* Use OpenAI function calling for predictable invocation
* Feed memory/context into reasoning function
* Use prompt chaining or retrieval to reduce hallucination
* Fall back to default behavior or clarifying question if tool match is unclear

---

## Pseudocode for Key Modules

### `main.py`

```python
def safety_check(planned_action):
    if action_involves_movement(planned_action):
        if child_detected_nearby():
            return "STOP"
    return "PROCEED"

def robust_tool_execution(tool_call):
    try:
        return TOOLS[tool_call.name](**tool_call.args)
    except Exception as e:
        log_error(e)
        return respond(f"Hmm, I had trouble doing that.")

while True:
    if wakeword_detected():
        audio = record_audio()
        transcript = speech_to_text(audio)
        if is_moderated(transcript):
            respond("I'm not allowed to talk about that.")
        else:
            tool_call = decide_action(transcript, memory)
            if safety_check(tool_call) == "PROCEED":
                result = robust_tool_execution(tool_call)
```

### `wakeword.py`

```python
def wakeword_detected():
    # Use Porcupine or local VAD to wait for "Hey Robot"
    return porcupine.detect("hey robot")
```

### `stt.py`

```python
def speech_to_text(audio):
    # Send to OpenAI Whisper API
    return openai.whisper.transcribe(audio)
```

### `tts.py`

```python
def respond(text):
    audio = google_tts(text)
    play_audio(audio)
```

### `recognize.py`

```python
class PrivacyProtectedFaceRecognition:
    def __init__(self):
        self.local_embeddings = load_family_embeddings()  # Never sent to cloud

    def recognize_face(self, frame):
        embedding = extract_face_embedding_local(frame)
        return compare_local(embedding, self.local_embeddings)
```

### `navigation.py`

```python
def find_and_notify(name):
    for room in ROOMS:
        go_to(room)
        frame = capture()
        if recognize_faces(frame) == name:
            respond(f"Hi {name}, it's time for dinner.")
            return
```

### `memory_manager.py`

```python
def update_memory(input, output=None):
    if "remember" in input:
        extract_fact_and_store(input)
    if output:
        log_conversation(input, output)

def get_context():
    return summarize_recent_conversations()
```

### `google_assistant.py`

```python
def execute_home_command(text):
    # Send text command to Assistant API
    assistant.send_command(text)
```

### `moderation.py`

```python
def is_moderated(text):
    flags = openai.moderate(text)
    return flags.violates_policy
```

---

## Future Enhancements (Optional)

* **Streaming STT**: Implement chunk-based speech recognition for sub-300ms latency if responsiveness becomes a bottleneck.
* **Semantic Memory**: Use FAISS + SentenceTransformers for vector-based long-term memory retrieval.
* **Vision-Language-Action (VLA) Models**: Evaluate π0.5 or OpenVLA for embodied reasoning if more sophisticated spatial planning is needed.
* **Google Home APIs**: Consider switching from Google Assistant SDK to the newer Google Home APIs for faster LAN-based control.
* **Hardware-Based Tuning**: Dynamically adjust frame rate or model size based on Pi hardware version (e.g. Pi 5 vs Pi 4).

---

This structure makes the system modular, agentic, safety-conscious, and ready for real-world interaction with gradual future upgrades.
