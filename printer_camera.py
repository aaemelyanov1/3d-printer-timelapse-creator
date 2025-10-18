import serial
import time
import cv2
import os
import logging
import keyboard

# Connection settings
PORT = 'COM3'  # Replace with your port (e.g., /dev/ttyUSB0 for Linux)
BAUDRATE = 115200  # Baud rate (usually 115200 for 3D printers)

# Screenshot save path
SAVE_FOLDER = r"C:\Timelabs\Screenshots"

# Maximum camera resolution
CAMERA_WIDTH = 2560  # 2560 or 1920
CAMERA_HEIGHT = 1440  # 1440 or 1080

# Camera URL (HTTP)
CAMERA_HTTP_URL = "http://192.168.31.200:8080/video"  # URL for HTTP stream

# Logging setup
logging.basicConfig(filename='printer_camera.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Function to connect to printer
def connect_to_printer(port, baudrate):
    try:
        printer = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to printer on {port}")
        logging.info(f"Connected to printer on {port}")
        return printer
    except serial.SerialException as e:
        print(f"Connection error: {e}")
        logging.error(f"Connection error: {e}")
        return None

def connect_to_camera(url):
    """
    Connects to camera by specified URL.
    Returns VideoCapture object or None if connection failed.
    """
    logging.info(f"Attempting to connect to camera at URL: {url}")
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        logging.error(f"Failed to connect to camera at URL: {url}")
        print(f"Failed to connect to camera at URL: {url}")
        return None
    logging.info(f"Successfully connected to camera at URL: {url}")
    return cap

def capture_webcam_image(save_folder, counter):
    """
    Captures image from camera and saves it to folder.
    Returns updated counter.
    """
    logging.info(f"Attempting to capture image #{counter}")
    # Create folder if it doesn't exist
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # Connect to camera via HTTP
    cap = connect_to_camera(CAMERA_HTTP_URL)
    if cap is None:
        logging.error("Failed to connect to camera via HTTP.")
        return counter

    # Set maximum resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    # Read frame from camera
    ret, frame = cap.read()
    if not ret:
        logging.error("Failed to capture frame.")
        return counter

    # Save frame with natural number sequence name
    image_path = os.path.join(save_folder, f"{counter}.jpg")
    cv2.imwrite(image_path, frame)
    logging.info(f"Frame saved: {image_path}")
    print(f"Frame saved: {image_path}")

    # Close camera
    cap.release()
    time.sleep(0.5)
    return counter + 1

# Main function
def main():
    printer = connect_to_printer(PORT, BAUDRATE)
    if not printer:
        return

    # Counter for file names
    counter = 1

    try:
        while True:
            # Check if 'm' key is pressed
            if keyboard.is_pressed('m'):  # If 'm' key pressed
                printer.write(b'M118 Smile\n')  # Send M118 command
                print("M118 Smile command sent to printer.")
                logging.info("M118 command sent to printer.")
                time.sleep(0.5)  # Delay to avoid multiple sends

            # Read data from serial port
            if printer.in_waiting > 0:
                try:
                    # Read line from port
                    response = printer.readline().decode().strip()
                    print(f"Printer response: {response}")
                    logging.info(f"Printer response: {response}")

                    # Check if response contains "Smile"
                    if 'Smile' in response:
                        print("Received 'Smile' message. Taking screenshot...")
                        logging.info("Received 'Smile' message. Taking screenshot...")
                        counter = capture_webcam_image(SAVE_FOLDER, counter)
                        time.sleep(5)  # Delay to avoid multiple screenshots in a row
                except UnicodeDecodeError as e:
                    print(f"Data decoding error: {e}")
                    logging.error(f"Data decoding error: {e}")
                except serial.SerialException as e:
                    print(f"Data read error: {e}")
                    logging.error(f"Data read error: {e}")

            time.sleep(0.1)  # Small delay to reduce CPU load
    except KeyboardInterrupt:
        print("Program finished.")
        logging.info("Program finished.")
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Error: {e}")
    finally:
        if printer:
            printer.close()
            print("Printer connection closed.")
            logging.info("Printer connection closed.")

if __name__ == "__main__":
    main()