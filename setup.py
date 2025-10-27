from setuptools import setup, find_packages

setup(
    name="family-robot",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "picarx>=0.1.0",
        "robot-hat>=0.1.0",
        "opencv-python>=4.5.0",
        "numpy>=1.19.0",
        "python-dotenv>=0.19.0",
        "openai>=0.27.0",
        "SpeechRecognition>=3.8.1",
        "pyaudio>=0.2.11",
        "vilib>=1.0.0",
        "RPi.GPIO>=0.7.0",
        "pyserial>=3.5",
        "pyserial-asyncio>=0.6"
    ],
    python_requires=">=3.7",
    author="Your Name",
    author_email="your.email@example.com",
    description="A smart, voice-controlled robot assistant for the PiCar-X platform",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/family-robot",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
