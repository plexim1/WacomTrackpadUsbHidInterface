import board
import busio
import usb_hid
from adafruit_hid.mouse import Mouse

# Initialize UART for serial communication
uart = busio.UART(board.GP0, board.GP1, baudrate=115200, timeout=0.1)

# Initialize HID mouse
mouse = Mouse(usb_hid.devices)

def process_command(command):
    try:
        parts = command.strip().split()
        cmd_type = parts[0]

        if cmd_type == 'M':  # Movement
            dx = int(parts[1])
            dy = int(parts[2])
            mouse.move(x=dx, y=dy)

        elif cmd_type == 'B':  # Button press
            if parts[1] == 'L':
                mouse.press(Mouse.LEFT_BUTTON)
            elif parts[1] == 'M':
                mouse.press(Mouse.MIDDLE_BUTTON)
            elif parts[1] == 'R':
                mouse.press(Mouse.RIGHT_BUTTON)

        elif cmd_type == 'R':  # Button release
            if parts[1] == 'L':
                mouse.release(Mouse.LEFT_BUTTON)
            elif parts[1] == 'M':
                mouse.release(Mouse.MIDDLE_BUTTON)
            elif parts[1] == 'R':
                mouse.release(Mouse.RIGHT_BUTTON)

        elif cmd_type == 'S':  # Scroll
            scroll_value = int(parts[1])
            mouse.move(wheel=scroll_value)

    except (ValueError, IndexError) as e:
        print(f"Invalid command format: {command}, Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {command}, Error: {e}")

def safe_decode(raw_data):
    try:
        return raw_data.decode('utf-8').strip()  # Attempt UTF-8 decoding
    except Exception as e:
        print(f"Decoding error: {raw_data}, Error: {e}")
        return ""  # Return an empty string for invalid data

# Main loop
while True:
    try:
        if uart.in_waiting > 0:
            raw_data = uart.readline()  # Read raw bytes
            if raw_data:
                command = safe_decode(raw_data)
                if command:  # Only process non-empty commands
                    print(f"Decoded command: {command}")  # Debug output
                    process_command(command)
    except Exception as e:
        print(f"Error reading UART: {e}")
