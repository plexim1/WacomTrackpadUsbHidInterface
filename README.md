# Interface to use Wacom tablet as a regular trackpad/touchpad without needing additional drivers (USB HID device).
This project creates a USB mouse interface for a Wacom tablet, eliminating the need for additional Windows drivers to use it as a touchpad.  It uses a Raspberry Pi 1 Model B running Raspberry Pi OS Lite to interpret Wacom tablet data and a Raspberry Pi Pico to act as a USB HID mouse.

The final product will consist of:
- A Raspberry Pi Pico running CircuitPython to function as a USB HID mouse.
- A Raspberry Pi 1 Model B running a custom script to read Wacom tablet data via evtest and translate it into a serial communication protocol.
- A Wacom tablet connected to the Raspberry Pi 1 Model B.
- Serial communication between the Raspberry Pi 1 Model B and the Raspberry Pi Pico.

# Serial Communication Format

## Protocol for sending commands to the Pico:

    Movement: M x y
    Example: M 10 -5 (move 10 units right, 5 units up).
    Button Press: B L / B M / B R
    Example: B L (press left button).
    Button Release: R L / R M / R R
    Example: R L (release left button).
    Scroll: S d
    Example: S -1 (scroll down one unit).



## Wiring Between Pico and RPI1

    Connect Pico UART Pins:
        Pico GP0 (UART TX) → RPI1 RX (GPIO 15)
        Pico GP1 (UART RX) → RPI1 TX (GPIO 14)
        Pico GND → RPI1 GND

    Power Supply:
    The Pico can remain connected to the computer for power and HID functionality.


# How to install

## Raspberry Pi Pico
- Install CircuitPython
- Copy the files from ./PICO

## Raspberry Pi
- Install Raspberry Pi OS Lite
- Copy content of ./RPI to /
- run /opt/prereqs.sh

## What's remaining
- Connect the boards together as explained over
- Connect the Pico with USB to your computer
- Connect Wacom tablet to the Raspberry Pi
- Power the Raspberry Pi
Everything should start up and the script should recognize the Wacom device automatically. You can now use the Wacom tablet as a trackpad utilising generic HID drivers on your Windows computer.