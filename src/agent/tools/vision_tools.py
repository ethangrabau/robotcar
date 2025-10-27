"""
Vision Tools for the Robot Agent

This module provides tools for visual analysis using the camera and vision models.
"""

import os
import logging
import time
from typing import Any, Dict, Optional
import base64
import json
import requests
from openai import OpenAI

from ..tools.base_tool import BaseTool, ToolExecutionError
from ...vision.camera import Camera

logger = logging.getLogger(__name__)

class AnalyzeSceneTool(BaseTool):
    """
    A tool for analyzing the scene in front of the robot using vision models.
    
    This tool captures an image using the robot's camera and sends it to
    a vision model for analysis, returning the model's textual response.
    """
    
    name = "analyze_scene"
    description = "Captures an image and analyzes what the robot sees"
    parameters = {
        "query": {
            "type": str,
            "description": "The question or instruction for analyzing the scene",
            "required": True
        },
        "save_image": {
            "type": bool,
            "description": "Whether to save the captured image",
            "required": False,
            "default": True
        },
        "image_dir": {
            "type": str,
            "description": "Directory to save the image in",
            "required": False,
            "default": "captured_images"
        }
    }
    
    def __init__(self):
        """Initialize the AnalyzeSceneTool."""
        self.camera = Camera()
        self.client = None
        
        # Try to initialize the OpenAI client
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                logger.warning("OPENAI_API_KEY not found in environment variables")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool to analyze the scene.
        
        Args:
            query: The question or instruction for analyzing the scene
            save_image: Whether to save the captured image
            image_dir: Directory to save the image in
            
        Returns:
            Dict containing the analysis result and image path if saved
        """
        self.validate_parameters(**kwargs)
        
        query = kwargs.get("query")
        save_image = kwargs.get("save_image", True)
        image_dir = kwargs.get("image_dir", "captured_images")
        
        # Ensure the OpenAI client is initialized
        if not self.client:
            try:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ToolExecutionError("OPENAI_API_KEY not found in environment variables")
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                raise ToolExecutionError(f"Failed to initialize OpenAI client: {str(e)}")
        
        # Capture image
        logger.info(f"Capturing image for query: {query}")
        
        # Ensure camera is started
        if not self.camera.is_running:
            if not self.camera.start():
                raise ToolExecutionError("Failed to start camera")
        
        # Save the image if requested
        image_path = None
        if save_image:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            os.makedirs(image_dir, exist_ok=True)
            image_path = self.camera.save_frame(f"scene_{timestamp}", directory=image_dir)
            
            if not image_path:
                raise ToolExecutionError("Failed to save image")
            
            logger.info(f"Image saved to {image_path}")
        else:
            # If not saving, still need to capture a frame
            frame = self.camera.capture_frame()
            if frame is None:
                raise ToolExecutionError("Failed to capture frame")
        
        # Analyze the image
        try:
            result = self._analyze_image(image_path, query)
            
            return {
                "success": True,
                "analysis": result,
                "image_path": image_path if save_image else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise ToolExecutionError(f"Failed to analyze image: {str(e)}")
    
    def _analyze_image(self, image_path: str, query: str) -> str:
        """
        Analyze the image using the OpenAI Vision API.
        
        Args:
            image_path: Path to the image file
            query: The question or instruction for analyzing the scene
            
        Returns:
            The model's textual response
        """
        try:
            # Read the image file
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create the messages payload
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use the appropriate model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes images captured by a robot's camera."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            # Extract the response text
            result = response.choices[0].message.content
            logger.info(f"Analysis result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in _analyze_image: {str(e)}")
            raise
