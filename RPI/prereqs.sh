#!/bin/bash

sudo apt update
# Missing some "sudo apt install"s

stty -F /dev/ttyAMA0 115200 cs8 -cstopb -parenb