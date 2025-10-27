PiCar-X GPT Voice Assistant: System Design Overview

Goal

To create a playful, voice-controlled robot assistant using a Raspberry Pi 5 + PiCar-X 2.0 platform that:

Listens via USB microphone

Responds via GPT-generated text + text-to-speech

Executes structured actions from GPT responses (e.g., movement, sounds)

Optionally integrates vision, memory, and tool-based function calling over time

Components

Hardware

Raspberry Pi 5

SunFounder PiCar-X 2.0 Robot Hat

USB Microphone

Built-in speaker connected via J20 (enabled by GPIO 20)

Software Stack

OS: Raspberry Pi OS (64-bit, Bookworm)

TTS: espeak (text-to-speech)

STT: openai-whisper, SpeechRecognition

GPT API: OpenAI gpt-4o, optionally using Assistants API

Python Framework: PiCar-X examples (gpt_car.py)

User Flow

User speaks into USB mic

Audio is captured and transcribed (via Whisper or SpeechRecognition)

Transcription is sent to GPT-4o along with assistant instructions

GPT returns a JSON-formatted response, e.g.:

{
  "actions": ["start engine", "honking"],
  "answer": "Let's go! I'm ready to roll!"
}

The robot:

Speaks the answer via espeak

Maps and executes any actions[]

Configuration Details

System Prompt (Assistant Personality)

The assistant is configured to:

Behave like a playful robot car ("PaiCar-X")

Return actions in a JSON array

Use a cheerful, optimistic tone with metaphors and robot quirks

keys.py

Holds:

OPENAI_API_KEY = "sk-..."
OPENAI_ASSISTANT_ID = "asst_..."  # optional

Features Implemented

✅ USB mic audio input

✅ GPT-4o assistant query

✅ Action JSON parsing

✅ Robot motion and sound control

✅ Speaker output via GPIO 20

✅ Voice output using TTS (espeak)

Planned Enhancements

Function Calling (OpenAI Tools)

Define structured functions for each action (e.g., say(text), drive_forward(), look_for_face(name), etc.)

GPT will choose tools directly

Memory

Add file search or embedding-based memory system

Store facts, descriptions, or face embeddings for recognition tasks

Advanced Behaviors

Use vision system to find people/objects

Add behavior chaining (e.g., "go find Kurt and tell him it’s time to go")

Add code interpreter tool for dynamic Python execution

Voice Output Function (Added to gpt_car.py)

def speak(text):
    import subprocess
    subprocess.run(["espeak", text])

Usage:

speak(response_text)

Where response_text is the GPT-generated answer string.

Development Notes for Windsurf

All logic currently lives in gpt_car.py

actions[] returned by GPT should be mapped to function calls inside Python

Audio output depends on pinctrl set 20 op dh to enable speaker

Use sudo for any run involving audio

To extend capabilities:

Add new JSON-based actions

Move to OpenAI function calling for better structure

Add a modular memory layer for context + retrieval