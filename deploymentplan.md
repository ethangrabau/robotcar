# Deployment & Implementation Plan for Embodied AI Family Assistant Robot

This document outlines a step-by-step implementation strategy for building, testing, and deploying the family assistant robot. Each phase builds logically on the last to ensure reliability, debuggability, and modular development.

---

## Step 1: Environment Setup and Hello World

**Goal**: Confirm Raspberry Pi setup and code deploys and runs remotely.

* [ ] Flash Raspberry Pi OS onto SD card
* [ ] Enable SSH and connect Pi to WiFi
* [ ] SSH into Pi: `ssh pi@<robot_ip>`
* [ ] Install Python 3.10+, pip, and virtualenv
* [ ] Run a `main.py` with a `print("Hello, robot!")` to confirm execution

---

## Step 2: Create Modular Skeleton

**Goal**: Prepare directory structure and create stub modules.

* [ ] Set up folder tree: `voice/`, `vision/`, `memory/`, `agentic/`, etc.
* [ ] Create all files with placeholder functions and docstrings
* [ ] Confirm `main.py` can import from all submodules without error

---

## Step 3: Basic Local-Only Voice Pipeline

**Goal**: Validate Whisper STT and Google TTS in isolation (on your dev machine).

1. `voice/stt.py`

   * [ ] Load audio file
   * [ ] Transcribe with OpenAI Whisper API
2. `voice/tts.py`

   * [ ] Synthesize speech from text via Google TTS API
   * [ ] Save audio to file and play it back
3. Integration Test

   * [ ] Record short clip → STT → ChatGPT → TTS → audio

Test locally **before** deploying to Pi.

---

## Step 4: Deploy Voice Pipeline to Pi

**Goal**: Enable full audio interaction on the robot.

* [ ] Connect USB mic and speaker to Pi
* [ ] Test recording mic input and playing audio
* [ ] Deploy working `stt.py` and `tts.py`
* [ ] Run a simple voice loop: record → transcribe → respond → speak

---

## Step 5: Add Wake Word Detection

**Goal**: Add Porcupine or keyword trigger to reduce unnecessary transcription.

* [ ] Install Porcupine SDK
* [ ] Replace manual start with wake word trigger
* [ ] Confirm detection with print/log

---

## Step 6: Add Moderation and Error Handling

**Goal**: Ensure responses are family-friendly and system doesn't crash.

* [ ] `filtering/moderation.py` with OpenAI Moderation API
* [ ] Wrap tool calls with `robust_tool_execution()`
* [ ] Print fallback message on failure

---

## Step 7: Reasoning + Tool Interface (No Real Tools Yet)

**Goal**: Let the LLM return a function name to call, using dummy tools.

1. `agentic/tools.py`

   * [ ] Define test tools: `speak(text)`, `fake_tool()`
2. `agentic/reasoning.py`

   * [ ] Register tool definitions with OpenAI
   * [ ] Call model with prompt → parse tool call
   * [ ] Confirm correct function name + args

---

## Step 8: Add Basic Real Tools

**Goal**: Wire up real tools in the same format.

* [ ] Implement `google_assistant.py` to send commands
* [ ] Add `speak`, `turn_on_light`, `get_profile_info` to registry
* [ ] Test "Turn off the kitchen lights" → executes tool

---

## Step 9: Vision System: Face Recognition

**Goal**: Build local-only recognition and test live camera input.

* [ ] `vision/recognize.py` loads known encodings
* [ ] Captures frame and finds faces
* [ ] Matches against local database and returns name
* [ ] Test with images + live camera feed

---

## Step 10: Navigation + Face Scan Loop

**Goal**: Robot physically patrols and recognizes family.

* [ ] Implement `navigation.py` for driving + avoiding obstacles
* [ ] Add loop to scan room-by-room for a face match
* [ ] On match, trigger a `speak()` tool call

---

## Step 11: Memory Management

**Goal**: Enable persistent profiles and summary context.

* [ ] Implement `memory_manager.py` to log past interactions
* [ ] Store JSON profile for each person (likes, routines, etc.)
* [ ] Integrate into `reasoning.py` context prompt

---

## Step 12: Safety Layer + Real Deployment

**Goal**: Ensure robot acts responsibly and consistently.

* [ ] Add `safety_check()` before all motion
* [ ] Confirm fail-safe for motion when children are too close
* [ ] Finalize logs, retries, fallback messages
* [ ] Run in real family environment

---

## Future Optional Steps

* [ ] Streaming STT for low-latency responsiveness
* [ ] Semantic memory using FAISS embeddings
* [ ] Vision-Language-Action planning models
* [ ] Offline fallback mode for low-connectivity usage
* [ ] Integrate new Google Home Local APIs (if needed)

---

By testing each core module locally, then integrating progressively on the Pi, we minimize complexity while validating system behavior at every step.
