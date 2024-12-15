#!/bin/bash

# Update the package list
sudo apt update -y

# Install required packages without manual confirmation
sudo apt-get install -y python3-evdev
sudo apt-get install -y python3-pyserial
sudo apt-get install -y evtest

# Configure the serial port
stty -F /dev/ttyAMA0 115200 cs8 -cstopb -parenb
