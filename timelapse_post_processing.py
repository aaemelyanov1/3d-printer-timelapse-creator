import sys
import os

# Parameters to customize
TRIGGER_COMMAND = "M118 Smile"  # G-code command to trigger the camera
INSERT_FREQUENCY = 1            # Take a photo every N layers (1 = every layer, 2 = every 2nd layer, etc.)
PAUSE_LENGTH = 1000             # Pause after triggering the camera (in milliseconds)
PARK_PRINT_HEAD = True          # Park the print head out of the way for the photo
HEAD_PARK_X = 10                # X position to park the print head
HEAD_PARK_Y = 125               # Y position to park the print head
ZHOP_HEIGHT = 2.0               # Z-hop height when parking (in mm)
ANTI_SHAKE_LENGTH = 0           # Pause before taking the photo (in milliseconds)
ENSURE_FINAL_IMAGE = True       # Ensure a final image is taken at the end of the print

# Path to the error log file
ERROR_LOG_FILE = os.path.join(os.path.dirname(__file__), "errors.log")

def log_error(message):
    """Log an error message to the error log file."""
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(message + "\n")

def extract_parameter(gcode, parameter_name):
    """
    Extract a parameter value from the G-code comments.
    Returns None if the parameter is not found.
    """
    for line in gcode.split("\n"):
        if f"; {parameter_name} =" in line:
            return float(line.split("=")[1].strip())
    return None

def is_main_layer_height(z, first_layer_height, layer_height):
    """
    Check if the current Z height corresponds to a main layer height.
    Main layer heights are first_layer_height + N * layer_height, where N is an integer.
    """
    if layer_height == 0:
        return False  # Avoid division by zero
    # Calculate N
    n = (z - first_layer_height) / layer_height
    # Check if N is an integer (with a small tolerance for floating-point inaccuracies)
    return abs(n - round(n)) < 0.001

def post_process_gcode(gcode):
    layers = gcode.split("\n")
    modified_gcode = []
    layer_count = 0
    last_x = 0
    last_y = 0
    last_z = 0

    # Extract first_layer_height and layer_height from the G-code
    first_layer_height = extract_parameter(gcode, "first_layer_height")
    layer_height = extract_parameter(gcode, "layer_height")

    if first_layer_height is None or layer_height is None:
        log_error("Error: Could not find first_layer_height or layer_height in G-code!")
        sys.exit(1)

    # Flag to track if we are waiting for the retract command
    waiting_for_retract = False

    for line in layers:
        # Track X, Y, Z location
        if line.startswith("G0") or line.startswith("G1") or line.startswith("G2") or line.startswith("G3"):
            if "X" in line:
                last_x = float(line.split("X")[1].split(" ")[0])
            if "Y" in line:
                last_y = float(line.split("Y")[1].split(" ")[0])
            if "Z" in line:
                last_z = float(line.split("Z")[1].split(" ")[0])

        # Check if the line indicates a new layer
        if ";LAYER_CHANGE" in line:
            # Check if the current height matches a main layer height
            if is_main_layer_height(last_z, first_layer_height, layer_height):
                layer_count += 1
                # Set the flag to wait for the retract command
                waiting_for_retract = True

        # Add the current line to the modified G-code
        modified_gcode.append(line)

        # If we are waiting for the retract command, check if the current line is a retract
        if waiting_for_retract and "G1" in line and "E-" in line:
            # Reset the flag
            waiting_for_retract = False

            # Check if it's time to take a photo based on the insert frequency
            if layer_count % INSERT_FREQUENCY == 0:
                # Add the camera trigger code after the retract command
                modified_gcode.append("; TimeLapse Script Begin")

                # For the first layer, do not move the print head
                if layer_count == 1:
                    # Trigger the camera without moving the print head
                    modified_gcode.append(f"{TRIGGER_COMMAND} ; Trigger camera")
                    modified_gcode.append(f"G4 P{PAUSE_LENGTH} ; Wait for camera")
                else:
                    # For subsequent layers, move the print head if enabled
                    if PARK_PRINT_HEAD:
                        # Z-hop to current layer height + 2 mm
                        z_hop_height = last_z + ZHOP_HEIGHT
                        modified_gcode.append(f"G0 F300 Z{z_hop_height} ; Z-hop")

                        modified_gcode.append(f"G0 F15000 X{HEAD_PARK_X} Y{HEAD_PARK_Y} ; Park print head")

                    # Wait for the printer to settle down (anti-shake)
                    if ANTI_SHAKE_LENGTH > 0:
                        modified_gcode.append(f"G4 P{ANTI_SHAKE_LENGTH} ; Wait for printer to settle")

                    # Wait for moves to finish before triggering the camera
                    modified_gcode.append("M400 ; Wait for moves to finish")

                    # Trigger the camera
                    modified_gcode.append(f"{TRIGGER_COMMAND} ; Trigger camera")

                    # Pause after the photo
                    modified_gcode.append(f"G4 P{PAUSE_LENGTH} ; Wait for camera")

                    # Restore the print head position
                    if PARK_PRINT_HEAD:
                        modified_gcode.append(f"G0 F15000 X{last_x} Y{last_y} ; Restore XY position")
                        modified_gcode.append(f"G0 F300 Z{last_z} ; Restore Z position")

                modified_gcode.append("; TimeLapse Script End")

    # Ensure a final image is taken at the end of the print
    if ENSURE_FINAL_IMAGE and "; Script Begin" not in modified_gcode[-1]:
        modified_gcode.append("; TimeLapse Final Image")
        modified_gcode.append("M400 ; Wait for moves to finish")
        modified_gcode.append(f"{TRIGGER_COMMAND} ; Trigger final camera")
        modified_gcode.append(f"G4 P{PAUSE_LENGTH} ; Wait for camera")

    return "\n".join(modified_gcode)

def main():
    # Check if the script received the correct number of arguments
    if len(sys.argv) < 2:
        log_error("Error: No input file provided.")
        log_error("Usage: python TimeLapse.py <input_gcode_file>")
        sys.exit(1)

    # Get the input file path from the command line arguments
    input_file = sys.argv[1]

    # Check if the input file exists
    if not os.path.exists(input_file):
        log_error(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    # Read the input G-code
    try:
        with open(input_file, "r") as f:
            input_gcode = f.read()
    except Exception as e:
        log_error(f"Error reading input file: {e}")
        sys.exit(1)

    # Check if input G-code is empty
    if not input_gcode:
        log_error("Error: Input G-code is empty!")
        sys.exit(1)

    # Process the G-code
    try:
        output_gcode = post_process_gcode(input_gcode)
    except Exception as e:
        log_error(f"Error processing G-code: {e}")
        sys.exit(1)

    # Write the output G-code back to the same file
    try:
        with open(input_file, "w") as f:
            f.write(output_gcode)
    except Exception as e:
        log_error(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()