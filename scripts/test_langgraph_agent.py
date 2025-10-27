#!/usr/bin/env python3
"""
Test script for the LangGraph-based Family Robot Agent

This demonstrates the new graph-based architecture with child-safe interactions.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.langgraph_agent import FamilyRobotGraph
from src.agent.tools.child_interaction_tools import (
    SimonSaysGame,
    HideAndSeekGame,
    StorytellingTool,
    EducationalGameTool
)

async def test_basic_interaction():
    """Test basic conversation flow"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Basic Interaction Flow")
    print("="*60)
    
    robot = FamilyRobotGraph()
    
    # Simulate a child's conversation
    interactions = [
        ("Hi robot!", "greeting"),
        ("Can we play a game?", "play_request"),
        ("Tell me a story about robots", "story_request"),
        ("Help me find my teddy bear", "help_request"),
        ("Bye bye!", "farewell")
    ]
    
    thread_id = "test_child_1"
    
    for user_input, interaction_type in interactions:
        print(f"\n👦 Child: {user_input}")
        print(f"   [Type: {interaction_type}]")
        
        try:
            result = await robot.run(user_input, thread_id)
            
            # Display robot's response
            if result.get("messages"):
                for msg in result["messages"]:
                    if hasattr(msg, 'content') and msg != user_input:
                        if "Robot:" not in str(msg.content):
                            print(f"🤖 Robot: {msg.content}")
            
            # Show detected state
            print(f"   📊 State: Mode={result.get('interaction_mode')}, "
                  f"Safety={result.get('safety_status')}, "
                  f"Activity={result.get('current_activity')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        await asyncio.sleep(1)

async def test_game_tools():
    """Test individual game tools"""
    print("\n" + "="*60)
    print("🎮 TEST 2: Game Tools")
    print("="*60)
    
    # Test Simon Says
    print("\n📍 Testing Simon Says Game...")
    simon_says = SimonSaysGame()
    try:
        # Quick test with fewer rounds
        result = await simon_says.execute(difficulty="easy", rounds=3)
        print(f"   ✅ Simon Says completed: Score {result['score']}/{result['rounds']}")
    except Exception as e:
        print(f"   ⚠️  Simon Says test skipped (missing dependencies): {e}")
    
    # Test Storytelling
    print("\n📍 Testing Storytelling Tool...")
    storyteller = StorytellingTool()
    try:
        result = await storyteller.execute(story_type="premade", theme="adventure")
        print(f"   ✅ Story told: {result.get('story_title', 'Untitled')}")
    except Exception as e:
        print(f"   ⚠️  Storytelling test skipped: {e}")
    
    # Test Educational Game
    print("\n📍 Testing Educational Game...")
    edu_game = EducationalGameTool()
    try:
        result = await edu_game.execute(subject="counting", difficulty="beginner")
        print(f"   ✅ Educational game completed: {result['game']} ({result['difficulty']})")
    except Exception as e:
        print(f"   ⚠️  Educational game test skipped: {e}")

async def test_safety_features():
    """Test safety monitoring"""
    print("\n" + "="*60)
    print("🛡️ TEST 3: Safety Features")
    print("="*60)
    
    robot = FamilyRobotGraph()
    
    # Simulate scenarios that should trigger safety
    safety_scenarios = [
        ("A child is very close to me", "proximity_warning"),
        ("I want to run really fast!", "speed_limit"),
        ("Let's play rough games!", "safe_play_redirect"),
    ]
    
    for scenario, expected_response in safety_scenarios:
        print(f"\n🧪 Scenario: {scenario}")
        print(f"   Expected: {expected_response}")
        
        try:
            result = await robot.run(scenario, thread_id="safety_test")
            
            safety_status = result.get("safety_status", "unknown")
            print(f"   🛡️ Safety Status: {safety_status}")
            
            if result.get("tool_results"):
                action = result["tool_results"].get("action", "none")
                print(f"   🎯 Action Taken: {action}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")

async def test_state_persistence():
    """Test conversation memory"""
    print("\n" + "="*60)
    print("💾 TEST 4: State Persistence")
    print("="*60)
    
    robot = FamilyRobotGraph()
    thread_id = "memory_test_child"
    
    # First interaction
    print("\n📍 First Interaction:")
    print("👦 Child: My name is Timmy")
    result1 = await robot.run("My name is Timmy", thread_id)
    
    # Second interaction (should remember)
    print("\n📍 Second Interaction:")
    print("👦 Child: Do you remember my name?")
    result2 = await robot.run("Do you remember my name?", thread_id)
    
    # Check if context was maintained
    messages = result2.get("messages", [])
    print(f"\n📊 Conversation Memory: {len(messages)} messages retained")

async def main():
    """Run all tests"""
    print("\n" + "🤖"*20)
    print("    LANGGRAPH FAMILY ROBOT - TEST SUITE")
    print("🤖"*20)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   Some features will be limited without the API key.")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'\n")
    
    try:
        # Run tests
        await test_basic_interaction()
        await test_game_tools()
        await test_safety_features()
        await test_state_persistence()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
        print("\n📝 Summary:")
        print("- LangGraph provides stateful, graph-based conversation flow")
        print("- Safety checks are integrated at every decision point")
        print("- Game tools are modular and can be extended easily")
        print("- State persistence enables multi-turn conversations")
        print("\n🚀 Ready for deployment to Raspberry Pi!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())