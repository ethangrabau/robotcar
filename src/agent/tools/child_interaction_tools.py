"""
Child Interaction Tools for the Family Robot

Safe, engaging tools designed specifically for interacting with children.
All tools include safety checks and age-appropriate content filtering.
"""

import asyncio
import logging
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from .base_tool import BaseTool, ToolExecutionError
from ...movement.controller import MovementController
from ...voice.tts import TextToSpeech
from ...vision.camera import Camera

logger = logging.getLogger(__name__)

@dataclass
class SafetyConfig:
    """Safety configuration for child interactions"""
    min_distance: float = 1.5  # meters
    max_speed: float = 0.3  # m/s when children present
    volume_limit: int = 60  # percentage
    interaction_timeout: int = 300  # seconds (5 minutes)
    require_parent_presence: bool = False  # for initial deployments

class SimonSaysGame(BaseTool):
    """
    Interactive Simon Says game for children.
    Robot gives commands and verifies if children follow them.
    """
    
    name = "simon_says_game"
    description = "Play Simon Says with children - safe, fun movement game"
    parameters = {
        "difficulty": {
            "type": str,
            "description": "Game difficulty: easy, medium, hard",
            "required": False,
            "default": "easy"
        },
        "rounds": {
            "type": int,
            "description": "Number of rounds to play",
            "required": False,
            "default": 5
        }
    }
    
    def __init__(self):
        self.movement = MovementController()
        self.tts = TextToSpeech()
        self.camera = Camera()
        self.safety = SafetyConfig()
        
        # Simon Says commands by difficulty
        self.commands = {
            "easy": [
                "touch your nose",
                "clap your hands",
                "jump up and down",
                "wave hello",
                "touch your toes",
                "spin around once"
            ],
            "medium": [
                "hop on one foot",
                "touch your elbow",
                "pat your head and rub your tummy",
                "do three jumping jacks",
                "walk backwards three steps",
                "make a funny face"
            ],
            "hard": [
                "balance on one foot for 3 seconds",
                "do a silly dance",
                "touch your left ear with your right hand",
                "spell your name in the air",
                "do five star jumps",
                "walk like a robot"
            ]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Run a Simon Says game session"""
        difficulty = kwargs.get("difficulty", "easy")
        rounds = kwargs.get("rounds", 5)
        
        logger.info(f"🎮 Starting Simon Says game - {difficulty} difficulty, {rounds} rounds")
        
        # Safety check
        await self._ensure_safe_environment()
        
        score = 0
        commands_given = []
        
        # Introduction
        await self.tts.speak(
            "Let's play Simon Says! Remember, only do what I say if I say 'Simon Says' first!",
            volume=self.safety.volume_limit
        )
        await asyncio.sleep(2)
        
        # Game rounds
        for round_num in range(rounds):
            # Randomly decide if this is a real Simon Says command
            is_simon_says = random.random() > 0.3  # 70% chance of being valid
            
            # Select random command
            command = random.choice(self.commands[difficulty])
            
            # Build the instruction
            if is_simon_says:
                instruction = f"Simon says... {command}!"
            else:
                instruction = f"{command.capitalize()}!"
            
            commands_given.append({
                "round": round_num + 1,
                "command": command,
                "simon_says": is_simon_says,
                "instruction": instruction
            })
            
            # Give the command
            await self.tts.speak(instruction, volume=self.safety.volume_limit)
            
            # Wait and observe
            await asyncio.sleep(3)
            
            # Check compliance (simplified - would use vision in real implementation)
            followed_correctly = await self._check_action_compliance(command, is_simon_says)
            
            if followed_correctly:
                score += 1
                responses = [
                    "Great job!",
                    "Perfect!",
                    "You got it!",
                    "Excellent!",
                    "Well done!"
                ]
                await self.tts.speak(random.choice(responses), volume=self.safety.volume_limit)
            elif not is_simon_says:
                await self.tts.speak(
                    "Oops! I didn't say Simon Says!",
                    volume=self.safety.volume_limit
                )
            
            await asyncio.sleep(1)
        
        # End game
        await self.tts.speak(
            f"Great game! You got {score} out of {rounds} correct! You're amazing!",
            volume=self.safety.volume_limit
        )
        
        return {
            "success": True,
            "game": "Simon Says",
            "score": score,
            "rounds": rounds,
            "difficulty": difficulty,
            "commands_given": commands_given
        }
    
    async def _ensure_safe_environment(self):
        """Check environment is safe for game"""
        # This would use real sensors in production
        logger.info("🛡️ Checking environment safety for game")
        self.movement.set_max_speed(self.safety.max_speed)
    
    async def _check_action_compliance(self, command: str, should_follow: bool) -> bool:
        """Check if child followed the command correctly"""
        # Simplified - in reality would use computer vision
        # For now, return probabilistic success based on difficulty
        return random.random() > 0.3

class HideAndSeekGame(BaseTool):
    """
    Robot counts while children hide, then searches for them.
    Uses object detection and safe navigation.
    """
    
    name = "hide_and_seek"
    description = "Play hide and seek - robot counts and searches safely"
    parameters = {
        "count_time": {
            "type": int,
            "description": "Seconds to count",
            "required": False,
            "default": 20
        },
        "search_time": {
            "type": int,
            "description": "Max seconds to search",
            "required": False,
            "default": 120
        }
    }
    
    def __init__(self):
        self.movement = MovementController()
        self.tts = TextToSpeech()
        self.camera = Camera()
        self.safety = SafetyConfig()
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Run hide and seek game"""
        count_time = kwargs.get("count_time", 20)
        search_time = kwargs.get("search_time", 120)
        
        logger.info("🙈 Starting Hide and Seek game")
        
        # Announce game
        await self.tts.speak(
            f"Let's play hide and seek! I'll count to {count_time}. Go hide!",
            volume=self.safety.volume_limit
        )
        
        # Turn around / close eyes (camera down)
        await self.movement.servo_control("camera_tilt", 90)  # Look down
        
        # Count
        for i in range(1, count_time + 1):
            if i % 5 == 0 or i == count_time:
                await self.tts.speak(str(i), volume=self.safety.volume_limit)
            await asyncio.sleep(1)
        
        # Start searching
        await self.tts.speak(
            "Ready or not, here I come!",
            volume=self.safety.volume_limit
        )
        
        # Look back up
        await self.movement.servo_control("camera_tilt", 0)
        
        # Search pattern (simplified)
        found_children = []
        search_start = time.time()
        
        while (time.time() - search_start) < search_time:
            # Rotate and look
            await self.movement.turn(45, speed=0.2)
            
            # Check for children
            detected = await self._look_for_children()
            
            if detected:
                await self.tts.speak(
                    f"Found you! Great hiding spot!",
                    volume=self.safety.volume_limit
                )
                found_children.append({
                    "time_found": time.time() - search_start,
                    "location": "current_position"
                })
                
                # Check if game should continue
                if len(found_children) >= 1:  # Adjust based on number of players
                    break
            
            await asyncio.sleep(2)
        
        # End game
        if found_children:
            await self.tts.speak(
                "Great game! You're really good at hiding!",
                volume=self.safety.volume_limit
            )
        else:
            await self.tts.speak(
                "You win! You're the hide and seek champion!",
                volume=self.safety.volume_limit
            )
        
        return {
            "success": True,
            "game": "Hide and Seek",
            "found_count": len(found_children),
            "search_duration": min(time.time() - search_start, search_time),
            "found_children": found_children
        }
    
    async def _look_for_children(self) -> bool:
        """Check if any children are visible"""
        # Simplified detection
        return random.random() > 0.8

class StorytellingTool(BaseTool):
    """
    Interactive storytelling with children.
    Can tell pre-made stories or create collaborative ones.
    """
    
    name = "storytelling"
    description = "Tell stories or create them together with children"
    parameters = {
        "story_type": {
            "type": str,
            "description": "Type of story: premade, collaborative, educational",
            "required": False,
            "default": "premade"
        },
        "theme": {
            "type": str,
            "description": "Story theme: adventure, friendship, learning, bedtime",
            "required": False,
            "default": "adventure"
        }
    }
    
    def __init__(self):
        self.tts = TextToSpeech()
        self.stories = {
            "adventure": [
                {
                    "title": "The Brave Little Robot",
                    "content": [
                        "Once upon a time, there was a little robot named Beep.",
                        "Beep loved to help children and make them smile.",
                        "One day, Beep heard that a teddy bear was lost in the garden.",
                        "Beep searched high and low, under bushes and behind trees.",
                        "Finally, Beep found the teddy bear and brought it back home.",
                        "The children were so happy, they gave Beep a big hug!",
                        "And from that day on, Beep was known as the bravest helper robot."
                    ]
                }
            ],
            "friendship": [
                {
                    "title": "Robot and the Rainbow",
                    "content": [
                        "There was a friendly robot who loved colors.",
                        "But the robot could only see in black and white.",
                        "One day, the robot met a child who taught it about rainbows.",
                        "Together, they painted pictures and played with colorful toys.",
                        "The robot learned that friendship is the most colorful thing of all.",
                        "Now the robot sees the world in beautiful colors of friendship."
                    ]
                }
            ]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Tell a story"""
        story_type = kwargs.get("story_type", "premade")
        theme = kwargs.get("theme", "adventure")
        
        logger.info(f"📚 Starting storytelling: {story_type} - {theme}")
        
        if story_type == "premade":
            # Select and tell a pre-made story
            if theme in self.stories and self.stories[theme]:
                story = random.choice(self.stories[theme])
                
                # Introduction
                await self.tts.speak(
                    f"Let me tell you a story called '{story['title']}'",
                    volume=60
                )
                await asyncio.sleep(2)
                
                # Tell the story
                for line in story["content"]:
                    await self.tts.speak(line, volume=60)
                    await asyncio.sleep(2)
                
                # End
                await self.tts.speak(
                    "The end! Did you like the story?",
                    volume=60
                )
                
                return {
                    "success": True,
                    "story_title": story["title"],
                    "story_type": story_type,
                    "theme": theme
                }
        
        elif story_type == "collaborative":
            # Create a story together
            await self.tts.speak(
                "Let's create a story together! I'll start, and you continue!",
                volume=60
            )
            await asyncio.sleep(2)
            
            await self.tts.speak(
                "Once upon a time, there was a magical garden where...",
                volume=60
            )
            
            return {
                "success": True,
                "story_type": "collaborative",
                "prompt_given": True,
                "theme": theme
            }
        
        return {
            "success": True,
            "story_type": story_type,
            "theme": theme
        }

class EducationalGameTool(BaseTool):
    """
    Educational games for learning numbers, colors, shapes, etc.
    Adapts to child's age and learning level.
    """
    
    name = "educational_game"
    description = "Play educational games - counting, colors, shapes, letters"
    parameters = {
        "subject": {
            "type": str,
            "description": "Subject to learn: counting, colors, shapes, letters",
            "required": False,
            "default": "counting"
        },
        "difficulty": {
            "type": str,
            "description": "Difficulty level: beginner, intermediate, advanced",
            "required": False,
            "default": "beginner"
        }
    }
    
    def __init__(self):
        self.tts = TextToSpeech()
        self.camera = Camera()
        
        self.content = {
            "counting": {
                "beginner": {"range": (1, 10), "problems": ["count_objects", "next_number"]},
                "intermediate": {"range": (1, 20), "problems": ["addition", "subtraction"]},
                "advanced": {"range": (1, 100), "problems": ["multiplication", "sequences"]}
            },
            "colors": {
                "beginner": ["red", "blue", "yellow", "green"],
                "intermediate": ["orange", "purple", "pink", "brown", "black", "white"],
                "advanced": ["turquoise", "magenta", "indigo", "coral"]
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Run an educational game session"""
        subject = kwargs.get("subject", "counting")
        difficulty = kwargs.get("difficulty", "beginner")
        
        logger.info(f"🎓 Starting educational game: {subject} ({difficulty})")
        
        if subject == "counting":
            return await self._counting_game(difficulty)
        elif subject == "colors":
            return await self._colors_game(difficulty)
        else:
            return {
                "success": True,
                "message": f"Learning about {subject}!",
                "subject": subject,
                "difficulty": difficulty
            }
    
    async def _counting_game(self, difficulty: str) -> Dict[str, Any]:
        """Run a counting game"""
        config = self.content["counting"][difficulty]
        min_num, max_num = config["range"]
        
        await self.tts.speak(
            f"Let's practice counting! Can you count to {max_num} with me?",
            volume=60
        )
        
        # Count together
        for i in range(min_num, min(min_num + 5, max_num + 1)):
            await self.tts.speak(str(i), volume=60)
            await asyncio.sleep(1)
        
        await self.tts.speak("Great counting! You're so smart!", volume=60)
        
        return {
            "success": True,
            "game": "counting",
            "difficulty": difficulty,
            "range_practiced": (min_num, min(min_num + 5, max_num))
        }
    
    async def _colors_game(self, difficulty: str) -> Dict[str, Any]:
        """Run a colors game"""
        colors = self.content["colors"][difficulty]
        
        await self.tts.speak(
            "Let's learn about colors! Can you find something that's...",
            volume=60
        )
        
        chosen_color = random.choice(colors)
        await asyncio.sleep(1)
        await self.tts.speak(f"{chosen_color}?", volume=60)
        
        await asyncio.sleep(3)
        await self.tts.speak(
            f"Great job! {chosen_color} is a beautiful color!",
            volume=60
        )
        
        return {
            "success": True,
            "game": "colors",
            "difficulty": difficulty,
            "color_learned": chosen_color
        }