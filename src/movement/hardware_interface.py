"""
Hardware Interface for PiCar-X

This module provides a clean, simplified interface to the PiCar-X hardware.
It abstracts away the low-level details and provides simple, direct methods
for controlling the robot's movement and sensors.
"""

from robot_hat import Pin, ADC, PWM, Servo, fileDB
from robot_hat import Grayscale_Module, Ultrasonic, utils
import time
import os

class PicarxController:
    """
    A class to control the PiCar-X robot hardware.
    
    This class provides simplified access to the core hardware functions
    of the PiCar-X robot, including movement, steering, camera control,
    and distance sensing.
    """
    
    CONFIG = '/opt/picar-x/picar-x.conf'

    # Constants for servo angle limits
    DIR_MIN = -30
    DIR_MAX = 30
    CAM_PAN_MIN = -90
    CAM_PAN_MAX = 90
    CAM_TILT_MIN = -35
    CAM_TILT_MAX = 65

    # PWM settings
    PERIOD = 4095
    PRESCALER = 10
    TIMEOUT = 0.02

    def __init__(self, 
                servo_pins:list=['P0', 'P1', 'P2'], 
                motor_pins:list=['D4', 'D5', 'P13', 'P12'],
                grayscale_pins:list=['A0', 'A1', 'A2'],
                ultrasonic_pins:list=['D2','D3'],
                config:str=CONFIG):
        """
        Initialize the PicarxController with the specified pins.
        
        Args:
            servo_pins: List of pins for [camera_pan, camera_tilt, direction] servos
            motor_pins: List of pins for [left_switch, right_switch, left_pwm, right_pwm]
            grayscale_pins: List of pins for the grayscale module
            ultrasonic_pins: List of pins for [trig, echo] of ultrasonic sensor
            config: Path to the configuration file
        """
        # Reset robot_hat
        utils.reset_mcu()
        time.sleep(0.2)

        # Config file
        self.config_file = fileDB(config, 777, os.getlogin())

        # Initialize servos
        self.cam_pan = Servo(servo_pins[0])
        self.cam_tilt = Servo(servo_pins[1])   
        self.dir_servo_pin = Servo(servo_pins[2])
        
        # Get calibration values
        self.dir_cali_val = float(self.config_file.get("picarx_dir_servo", default_value=0))
        self.cam_pan_cali_val = float(self.config_file.get("picarx_cam_pan_servo", default_value=0))
        self.cam_tilt_cali_val = float(self.config_file.get("picarx_cam_tilt_servo", default_value=0))
        
        # Set servos to init angle
        self.dir_servo_pin.angle(self.dir_cali_val)
        self.cam_pan.angle(self.cam_pan_cali_val)
        self.cam_tilt.angle(self.cam_tilt_cali_val)

        # Initialize motors
        self.left_rear_dir_pin = Pin(motor_pins[0])
        self.right_rear_dir_pin = Pin(motor_pins[1])
        self.left_rear_pwm_pin = PWM(motor_pins[2])
        self.right_rear_pwm_pin = PWM(motor_pins[3])
        self.motor_direction_pins = [self.left_rear_dir_pin, self.right_rear_dir_pin]
        self.motor_speed_pins = [self.left_rear_pwm_pin, self.right_rear_pwm_pin]
        
        # Get calibration values for motors
        self.cali_dir_value = self.config_file.get("picarx_dir_motor", default_value="[1, 1]")
        self.cali_dir_value = [int(i.strip()) for i in self.cali_dir_value.strip().strip("[]").split(",")]
        self.cali_speed_value = [0, 0]
        self.dir_current_angle = 0
        
        # Initialize PWM
        for pin in self.motor_speed_pins:
            pin.period(self.PERIOD)
            pin.prescaler(self.PRESCALER)

        # Initialize ultrasonic sensor
        trig, echo = ultrasonic_pins
        self.ultrasonic = Ultrasonic(Pin(trig), Pin(echo, mode=Pin.IN, pull=Pin.PULL_DOWN))

    def move_forward(self, speed):
        """
        Move the robot forward at the specified speed.
        
        Args:
            speed: Speed value between 0-100
        """
        self._set_motor_direction(speed)
        
    def move_backward(self, speed):
        """
        Move the robot backward at the specified speed.
        
        Args:
            speed: Speed value between 0-100
        """
        self._set_motor_direction(-speed)
        
    def _set_motor_direction(self, speed):
        """
        Helper method to set motor direction and speed.
        
        Args:
            speed: Speed value between -100 and 100, negative for backward
        """
        current_angle = self.dir_current_angle
        if current_angle != 0:
            abs_current_angle = abs(current_angle)
            if abs_current_angle > self.DIR_MAX:
                abs_current_angle = self.DIR_MAX
            power_scale = (100 - abs_current_angle) / 100.0
            
            if speed > 0:  # Forward
                if (current_angle / abs_current_angle) > 0:
                    self._set_motor_speed(1, speed * power_scale)
                    self._set_motor_speed(2, -speed)
                else:
                    self._set_motor_speed(1, speed)
                    self._set_motor_speed(2, -speed * power_scale)
            else:  # Backward
                if (current_angle / abs_current_angle) > 0:
                    self._set_motor_speed(1, speed)
                    self._set_motor_speed(2, -speed * power_scale)
                else:
                    self._set_motor_speed(1, speed * power_scale)
                    self._set_motor_speed(2, -speed)
        else:
            self._set_motor_speed(1, speed)
            self._set_motor_speed(2, -speed)

    def _set_motor_speed(self, motor, speed):
        """
        Set the speed of a specific motor.
        
        Args:
            motor: Motor index (1 for left, 2 for right)
            speed: Speed value between -100 and 100
        """
        # Constrain speed to -100, 100
        speed = max(-100, min(100, speed))
        
        motor -= 1  # Convert to 0-indexed
        
        if speed >= 0:
            direction = 1 * self.cali_dir_value[motor]
        else:
            direction = -1 * self.cali_dir_value[motor]
        
        speed = abs(speed)
        
        # Apply speed scaling
        if speed != 0:
            speed = int(speed / 2) + 50
            
        speed = speed - self.cali_speed_value[motor]
        
        if direction < 0:
            self.motor_direction_pins[motor].high()
            self.motor_speed_pins[motor].pulse_width_percent(speed)
        else:
            self.motor_direction_pins[motor].low()
            self.motor_speed_pins[motor].pulse_width_percent(speed)

    def turn(self, angle):
        """
        Turn the robot's front wheels to the specified angle.
        
        Args:
            angle: Angle between -30 (left) and 30 (right)
        """
        self.dir_current_angle = max(self.DIR_MIN, min(self.DIR_MAX, angle))
        angle_value = self.dir_current_angle + self.dir_cali_val
        self.dir_servo_pin.angle(angle_value)

    def stop(self):
        """
        Stop the robot's movement.
        """
        for _ in range(2):  # Execute twice to ensure it stops
            self.motor_speed_pins[0].pulse_width_percent(0)
            self.motor_speed_pins[1].pulse_width_percent(0)
            time.sleep(0.002)

    def set_camera_angle(self, pan, tilt):
        """
        Set the camera pan and tilt angles.
        
        Args:
            pan: Pan angle between -90 (left) and 90 (right)
            tilt: Tilt angle between -35 (down) and 65 (up)
        """
        # Set pan angle
        pan = max(self.CAM_PAN_MIN, min(self.CAM_PAN_MAX, pan))
        self.cam_pan.angle(-1 * (pan + -1 * self.cam_pan_cali_val))
        
        # Set tilt angle
        tilt = max(self.CAM_TILT_MIN, min(self.CAM_TILT_MAX, tilt))
        self.cam_tilt.angle(-1 * (tilt + -1 * self.cam_tilt_cali_val))

    def get_distance(self):
        """
        Get the distance from the ultrasonic sensor.
        
        Returns:
            float: Distance in centimeters
        """
        return self.ultrasonic.read()

    def reset(self):
        """
        Reset the robot to its default state.
        """
        self.stop()
        self.turn(0)
        self.set_camera_angle(0, 0)
