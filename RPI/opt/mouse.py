import serial
from evdev import InputDevice, list_devices, ecodes
import time

# ==========================
# Adjustable Parameters
# ==========================
MOVEMENT_SENSITIVITY = 0.3   # Cursor movement precision (lower = slower, smoother)
MOVEMENT_THRESHOLD = 1       # Minimum movement to avoid jitter
TAP_MOVEMENT_THRESHOLD = 2   # Max movement allowed to still register as a tap

SCROLL_SENSITIVITY = 0.5       # Smaller step size for smooth, precise scroll
SCROLL_THRESHOLD = 0           # Threshold eliminated for instant responsiveness
SCROLL_INPUT_SCALING = 0.01    # Fine-tune input sensitivity (lower = smoother)
INVERT_SCROLL = False          # Set True to invert scroll direction


TAP_TIMEOUT = 0.4            # Timeframe (seconds) for multi-finger taps
CLICK_THRESHOLD_TIME = 0.05  # Time threshold for detecting taps as clicks

# ==========================
# Helper Functions
# ==========================
def send_command(command, buffer, uart):
    """Buffer and send commands to the Pico via UART."""
    buffer.append(f"{command}\n")
    if len(buffer) >= 5:  # Batch commands to minimize UART overhead
        uart.write("".join(buffer).encode('utf-8'))
        buffer.clear()

def find_device_by_name(name):
    """Find the input device by its name."""
    for path in list_devices():
        device = InputDevice(path)
        if device.name == name:
            return device
    return None

def reset_state(state):
    """Reset touch states for movement, scrolling, and dragging."""
    state.update({
        "start_x": None,
        "start_y": None,
        "scroll_y": None,
        "dragging": False,
        "movement_detected": False
    })

def invert_scroll_direction(value):
    """Invert scroll direction if INVERT_SCROLL is enabled."""
    return -value if INVERT_SCROLL else value

# ==========================
# Gesture Handlers
# ==========================
def handle_single_finger_move(event, state, uart, buffer):
    """Handle smooth single-finger cursor movement."""
    if event.code == ecodes.ABS_X:
        if state["start_x"] is not None:
            dx = (event.value - state["start_x"]) * MOVEMENT_SENSITIVITY
            if abs(dx) > MOVEMENT_THRESHOLD:
                send_command(f"M {int(dx)} 0", buffer, uart)
                state["start_x"] = event.value
                state["movement_detected"] = True
        else:
            state["start_x"] = event.value
    elif event.code == ecodes.ABS_Y:
        if state["start_y"] is not None:
            dy = (event.value - state["start_y"]) * MOVEMENT_SENSITIVITY
            if abs(dy) > MOVEMENT_THRESHOLD:
                send_command(f"M 0 {int(dy)}", buffer, uart)
                state["start_y"] = event.value
                state["movement_detected"] = True
        else:
            state["start_y"] = event.value

def handle_two_finger_scroll(event, state, uart, buffer):
    """Handle smooth two-finger scrolling similar to dragging."""
    if event.code == ecodes.ABS_Y:
        if state["scroll_y"] is None:  # Initialize scroll_y on the first touch
            state["scroll_y"] = event.value
        else:
            # Treat input like dragging, scale it to smooth scroll steps
            dy = (event.value - state["scroll_y"]) * SCROLL_INPUT_SCALING
            scroll_step = invert_scroll_direction(int(dy * SCROLL_SENSITIVITY))

            # Only send a scroll command when the step exceeds threshold
            if abs(scroll_step) >= 1:  # Ensures smooth, small increments
                send_command(f"S {scroll_step}", buffer, uart)
                state["scroll_y"] = event.value  # Update position for continuous scrolling

def handle_taps(state, current_time, uart):
    """Handle single and two-finger taps."""
    if state["active_fingers"] == 1 and not state["movement_detected"]:
        if current_time - state["touch_start_time"] <= TAP_TIMEOUT:
            uart.write("B L\nR L\n".encode('utf-8'))  # Left click
    elif state["active_fingers"] == 2 and not state["movement_detected"]:
        if current_time - state["touch_start_time"] <= TAP_TIMEOUT:
            uart.write("B R\nR R\n".encode('utf-8'))  # Right click

def handle_three_finger_drag(event, state, uart, buffer):
    """Handle three-finger dragging."""
    if not state["dragging"]:
        send_command("B L", buffer, uart)  # Begin drag
        state["dragging"] = True
    handle_single_finger_move(event, state, uart, buffer)

# ==========================
# Main Event Loop
# ==========================
def main():
    # Initialize UART
    uart = serial.Serial('/dev/ttyAMA0', baudrate=115200, timeout=0.1)
    command_buffer = []

    # Detect Wacom device
    device_name = "Wacom Intuos Pro M Finger"
    input_device = find_device_by_name(device_name)
    if not input_device:
        print(f"Error: Device '{device_name}' not found.")
        return
    print(f"Listening to events from device: {input_device.name} ({input_device.path})")

    # State Management
    state = {
        "start_x": None,
        "start_y": None,
        "scroll_y": None,
        "scroll_accumulated": 0,
        "is_touching": False,
        "dragging": False,
        "movement_detected": False,
        "active_fingers": 0,
        "touch_start_time": 0,
    }

    try:
        for event in input_device.read_loop():
            current_time = time.time()

            if event.type == ecodes.EV_ABS:
                if state["is_touching"]:
                    if state["active_fingers"] == 1:
                        handle_single_finger_move(event, state, uart, command_buffer)
                    elif state["active_fingers"] == 2:
                        handle_two_finger_scroll(event, state, uart, command_buffer)
                    elif state["active_fingers"] == 3:
                        handle_three_finger_drag(event, state, uart, command_buffer)

            elif event.type == ecodes.EV_KEY:
                if event.code == ecodes.BTN_TOUCH:
                    if event.value == 1:  # Finger touched
                        state["is_touching"] = True
                        state["touch_start_time"] = current_time
                        reset_state(state)
                    elif event.value == 0:  # Finger lifted
                        handle_taps(state, current_time, uart)
                        if state["dragging"]:
                            send_command("R L", command_buffer, uart)
                            state["dragging"] = False
                        state["is_touching"] = False
                        state["active_fingers"] = 0
                        state["scroll_y"] = None  # Reset scroll reference position

                elif event.code in {ecodes.BTN_TOOL_FINGER, ecodes.BTN_TOOL_DOUBLETAP, ecodes.BTN_TOOL_TRIPLETAP}:
                    if event.code == ecodes.BTN_TOOL_FINGER:
                        state["active_fingers"] = 1 if event.value else 0
                    elif event.code == ecodes.BTN_TOOL_DOUBLETAP:
                        state["active_fingers"] = 2 if event.value else 0
                    elif event.code == ecodes.BTN_TOOL_TRIPLETAP:
                        state["active_fingers"] = 3 if event.value else 0

    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as e:
        print(f"Error: {e}")

# Run the main loop
if __name__ == "__main__":
    main()