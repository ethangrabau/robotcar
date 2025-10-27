#!/bin/bash
# Fix hardware paths and dependencies for PiCar-X

echo "Fixing hardware paths and dependencies for PiCar-X..."

# Create a symbolic link to the picarx module if it's not in the Python path
if [ -d "/usr/local/lib/python3.11/dist-packages/picarx" ]; then
  echo "picarx module found in system packages"
else
  echo "Creating symbolic link to picarx module"
  # Check common locations
  if [ -d "/home/pi/picar-x/lib/picarx" ]; then
    sudo ln -sf /home/pi/picar-x/lib/picarx /usr/local/lib/python3.11/dist-packages/
  elif [ -d "/home/pi/SunFounder_PiCar-X/picarx" ]; then
    sudo ln -sf /home/pi/SunFounder_PiCar-X/picarx /usr/local/lib/python3.11/dist-packages/
  else
    echo "Could not find picarx module. Please install it first."
  fi
fi

# Create a symbolic link to the robot_hat module if it's not in the Python path
if [ -d "/usr/local/lib/python3.11/dist-packages/robot_hat" ]; then
  echo "robot_hat module found in system packages"
else
  echo "Creating symbolic link to robot_hat module"
  # Check common locations
  if [ -d "/home/pi/picar-x/lib/robot_hat" ]; then
    sudo ln -sf /home/pi/picar-x/lib/robot_hat /usr/local/lib/python3.11/dist-packages/
  elif [ -d "/home/pi/SunFounder_PiCar-X/robot_hat" ]; then
    sudo ln -sf /home/pi/SunFounder_PiCar-X/robot_hat /usr/local/lib/python3.11/dist-packages/
  else
    echo "Could not find robot_hat module. Please install it first."
  fi
fi

# Create a symbolic link to the vilib module if it's not in the Python path
if [ -d "/usr/local/lib/python3.11/dist-packages/vilib" ]; then
  echo "vilib module found in system packages"
else
  echo "Creating symbolic link to vilib module"
  # Check common locations
  if [ -d "/home/pi/picar-x/lib/vilib" ]; then
    sudo ln -sf /home/pi/picar-x/lib/vilib /usr/local/lib/python3.11/dist-packages/
  elif [ -d "/home/pi/SunFounder_PiCar-X/vilib" ]; then
    sudo ln -sf /home/pi/SunFounder_PiCar-X/vilib /usr/local/lib/python3.11/dist-packages/
  else
    echo "Could not find vilib module. Please install it first."
  fi
fi

# Add the modules to the virtual environment
source ~/family-robot/venv/bin/activate
python -c "import sys; print('Python path:', sys.path)"
deactivate

echo "Hardware paths fixed!"
