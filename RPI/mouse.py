import serial
from evdev import InputDevice, list_devices, ecodes
import time

# Initialize UART for communication with the Pico
uart = serial.Serial('/dev/ttyAMA0', baudrate=115200, timeout=0.1)

command_buffer = []

def send_command(command):
    """Buffer and send commands to the Pico via UART."""
    command_buffer.append(f"{command}\n")
    if len(command_buffer) >= 5:  # Send in batches of 5
        uart.write("".join(command_buffer).encode('utf-8'))
        command_buffer.clear()

def find_device_by_name(name):
    """Find the input device by its name."""
    for path in list_devices():
        device = InputDevice(path)
        if device.name == name:
            return device
    return None

# Detect the Wacom Intuos Pro M Finger device
device_name = "Wacom Intuos Pro M Finger"
input_device = find_device_by_name(device_name)

if not input_device:
    print(f"Error: Device '{device_name}' not found.")
    exit(1)

print(f"Listening to events from device: {input_device.name} ({input_device.path})")

# Track movement relative to touch start
start_x, start_y = None, None
is_touching = False
movement_threshold = 2  # Minimum delta to consider meaningful movement
active_fingers = 0
movement_detected = False  # Flag to detect if movement occurred
dragging = False  # Track whether dragging is active
scrolling = False  # Track whether scrolling is active

# Sensitivity factors
movement_sensitivity = 0.5  # Lower value = slower movement
scroll_sensitivity = 1      # Set to 1 to send small, fixed scroll steps
scroll_input_scaling = 0.05  # Adjust this to change how much movement on the tablet triggers scrolling

# Main event loop
try:
    for event in input_device.read_loop():
        # Pre-filter events to minimize processing load
        if event.type not in {ecodes.EV_ABS, ecodes.EV_KEY}:
            continue

        if event.type == ecodes.EV_ABS:
            if is_touching:
                if active_fingers == 2 and not dragging:
                    # Two-finger scrolling
                    if event.code == ecodes.ABS_Y:
                        if start_y is None:
                            start_y = event.value
                        else:
                            scaled_dy = (event.value - start_y) * scroll_input_scaling
                            if abs(scaled_dy) >= 1:
                                scroll_direction = -1 if scaled_dy < 0 else 1  # Negative for up, positive for down
                                send_command(f"S {scroll_direction * scroll_sensitivity}")
                                start_y = event.value  # Update for continuous scrolling
                            scrolling = True
                elif active_fingers == 3:
                    # Three-finger dragging
                    if not dragging:
                        send_command("B L")  # Begin drag (left button pressed)
                        dragging = True
                    if event.code == ecodes.ABS_X:
                        if start_x is None:
                            start_x = event.value
                        else:
                            dx = (event.value - start_x) * movement_sensitivity
                            if abs(dx) > movement_threshold:
                                send_command(f"M {int(dx)} 0")
                                start_x = event.value
                    elif event.code == ecodes.ABS_Y:
                        if start_y is None:
                            start_y = event.value
                        else:
                            dy = (event.value - start_y) * movement_sensitivity
                            if abs(dy) > movement_threshold:
                                send_command(f"M 0 {int(dy)}")
                                start_y = event.value
                elif active_fingers == 1 and not scrolling:
                    # Single-finger movement
                    if event.code == ecodes.ABS_X:
                        if start_x is None:
                            start_x = event.value
                        else:
                            dx = (event.value - start_x) * movement_sensitivity
                            if abs(dx) > movement_threshold:
                                send_command(f"M {int(dx)} 0")
                                start_x = event.value  # Update start position to current
                                movement_detected = True

                    elif event.code == ecodes.ABS_Y:
                        if start_y is None:
                            start_y = event.value
                        else:
                            dy = (event.value - start_y) * movement_sensitivity
                            if abs(dy) > movement_threshold:
                                send_command(f"M 0 {int(dy)}")
                                start_y = event.value  # Update start position to current
                                movement_detected = True

        elif event.type == ecodes.EV_KEY:
            if event.code == ecodes.BTN_TOUCH:
                if event.value == 1:  # Finger touched the tablet
                    is_touching = True
                    start_x, start_y = None, None
                    movement_detected = False
                elif event.value == 0:  # Finger lifted
                    is_touching = False
                    if dragging:
                        send_command("R L")  # Release left button for drag
                        dragging = False
                    if scrolling:
                        scrolling = False  # End scrolling
                    elif not movement_detected:
                        # Immediately send click commands on release
                        if active_fingers == 1:
                            uart.write("B L\nR L\n".encode('utf-8'))  # Left click
                        elif active_fingers == 2:
                            uart.write("B R\nR R\n".encode('utf-8'))  # Right click
                    active_fingers = 0  # Reset fingers after release

            elif event.code in {ecodes.BTN_TOOL_FINGER, ecodes.BTN_TOOL_DOUBLETAP, ecodes.BTN_TOOL_TRIPLETAP}:
                # Track the number of active fingers
                if event.code == ecodes.BTN_TOOL_FINGER:
                    active_fingers = 1 if event.value == 1 else 0
                elif event.code == ecodes.BTN_TOOL_DOUBLETAP:
                    active_fingers = 2 if event.value == 1 else 0
                elif event.code == ecodes.BTN_TOOL_TRIPLETAP:
                    active_fingers = 3 if event.value == 1 else 0

except KeyboardInterrupt:
    print("Stopped by user.")
except Exception as e:
    print(f"Error: {e}")

