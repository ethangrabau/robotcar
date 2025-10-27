#!/usr/bin/env python3
"""
Simple script to set up the OpenAI API key on the Pi
"""

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Set up OpenAI API key')
    parser.add_argument('api_key', type=str, help='Your OpenAI API key')
    args = parser.parse_args()
    
    # Create keys.py file with the API key
    with open('keys.py', 'w') as f:
        f.write(f'OPENAI_API_KEY = "{args.api_key}"\n')
    
    print(f"✅ API key saved to keys.py")
    print(f"🔑 You can now run the object finder with: python3 standalone_object_finder.py")

if __name__ == "__main__":
    main()
