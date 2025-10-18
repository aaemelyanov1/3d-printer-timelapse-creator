import json
import logging
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime

import cv2
import keyboard
import serial
from PIL import Image, ImageTk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

# Default settings
DEFAULT_PORT = 'COM3'
DEFAULT_BAUDRATE = 115200
DEFAULT_SAVE_FOLDER = r"C:\Timelabs\Screenshots"
DEFAULT_CAMERA_WIDTH = 2560
DEFAULT_CAMERA_HEIGHT = 1440
DEFAULT_CAMERA_HTTP_URL = "http://192.168.31.200:8080/video"
DEFAULT_TEST_KEY = 'm'
DEFAULT_THEME = 'darkly'

# Logging setup
logging.basicConfig(filename='printer_camera.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Printer and camera functions
def connect_to_printer(port, baudrate):
    try:
        printer = serial.Serial(port, baudrate, timeout=1)
        logging.info(f"Connected to printer on {port}")
        return printer
    except serial.SerialException as e:
        logging.error(f"Connection error: {e}")
        return None

def connect_to_camera(url):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        logging.error(f"Failed to connect to camera at URL: {url}")
        return None
    return cap

def save_original_image(image, save_folder, prefix="", is_test=False):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if is_test:
        filename = os.path.join(save_folder, f"{prefix}{timestamp}.jpg")
    else:
        filename = os.path.join(save_folder, f"{timestamp}.jpg")

    # Save image
    image.save(filename)
    logging.info(f"Original image saved: {filename}")
    print(f"Original image saved: {filename}")
    return filename

def capture_webcam_image(save_folder, counter, prefix="", is_test=False, image_label=None):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    cap = connect_to_camera(CAMERA_HTTP_URL)
    if cap is None:
        return counter
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    ret, frame = cap.read()
    if not ret:
        return counter

    # Save original image
    original_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Form filename
    if is_test:
        image_name = f"{prefix}{counter}.jpg"
    else:
        image_name = f"{counter}.jpg"

    image_path = os.path.join(save_folder, image_name)
    original_img.save(image_path)
    logging.info(f"Original image saved: {image_path}")
    print(f"Original image saved: {image_path}")

    # Update image in interface
    if image_label:
        display_img = original_img.resize((350, 600), Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=display_img)
        image_label.config(image=imgtk)
        image_label.image = imgtk

    cap.release()
    time.sleep(0.5)
    return counter + 1

def send_command_to_printer(printer, command):
    try:
        printer.write((command + '\n').encode())
        logging.info(f"Command sent: {command}")
    except serial.SerialException as e:
        logging.error(f"Command send error: {e}")

def check_camera_thread(url, text_widget, image_label):
    cap = connect_to_camera(url)
    if cap:
        ret, frame = cap.read()
        if ret:
            # Save image in original resolution
            original_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            # Create reduced copy for display
            display_width = 350
            display_height = 600
            display_img = original_img.resize((display_width, display_height), Image.Resampling.LANCZOS)

            # Display reduced image in window
            imgtk = ImageTk.PhotoImage(image=display_img)
            image_label.config(image=imgtk)
            image_label.image = imgtk

            print("Camera connected successfully!")
        cap.release()
    else:
        print("Failed to connect to camera.")
    time.sleep(5)

# Main function
def main(printer, counter, test_counter, stop_event, enable_keyboard_capture, test_key, text_widget, image_label):
    try:
        while not stop_event.is_set():
            # Check if test key is pressed (if enabled)
            if enable_keyboard_capture.get() and keyboard.is_pressed(test_key.get()):
                print(f"Key {test_key.get()} pressed. Sending command 'M118 Smile'...")
                send_command_to_printer(printer, "M118 Smile")
                time.sleep(0.5)

            # Read data from serial port
            if printer and printer.is_open:
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
                            counter = capture_webcam_image(SAVE_FOLDER, counter, image_label=image_label)
                            time.sleep(5)
                    except UnicodeDecodeError as e:
                        print(f"Data decoding error: {e}")
                        logging.error(f"Data decoding error: {e}")
                    except serial.SerialException as e:
                        print(f"Data read error: {e}")
                        logging.error(f"Data read error: {e}")

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program finished.")
        logging.info("Program finished.")
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Error: {e}")
    finally:
        if printer and printer.is_open:
            printer.close()
            print("Printer connection closed.")
            logging.info("Printer connection closed.")

# Print output redirection to text widget
class PrintToText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

# GUI
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Santiago Timelapse")
        self.printer = None
        self.counter = 1
        self.test_counter = 1
        self.stop_event = threading.Event()

        # Variables for settings storage
        self.port = tk.StringVar(value=DEFAULT_PORT)
        self.baudrate = tk.IntVar(value=DEFAULT_BAUDRATE)
        self.save_folder = tk.StringVar(value=DEFAULT_SAVE_FOLDER)
        self.camera_width = tk.IntVar(value=DEFAULT_CAMERA_WIDTH)
        self.camera_height = tk.IntVar(value=DEFAULT_CAMERA_HEIGHT)
        self.camera_url = tk.StringVar(value=DEFAULT_CAMERA_HTTP_URL)
        self.enable_keyboard_capture = tk.BooleanVar(value=False)
        self.test_key = tk.StringVar(value=DEFAULT_TEST_KEY)
        self.theme = tk.StringVar(value=DEFAULT_THEME)

        # Create interface
        self.create_widgets()

        # Redirect print output to text widget
        sys.stdout = PrintToText(self.terminal)

    def create_widgets(self):
        # Create tabs
        self.notebook = ttkb.Notebook(self.root)
        self.main_tab = ttkb.Frame(self.notebook)
        self.settings_tab = ttkb.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.pack(expand=1, fill="both")

        # Main tab
        self.create_main_tab()

        # Settings tab
        self.create_settings_tab()

    def create_main_tab(self):
        # Settings edit fields
        ttkb.Label(self.main_tab, text="Port:", style="primary").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.port, width=40).grid(row=0, column=1, padx=5, pady=5)

        ttkb.Label(self.main_tab, text="Baudrate:", style="primary").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.baudrate, width=40).grid(row=1, column=1, padx=5, pady=5)

        ttkb.Label(self.main_tab, text="Save folder:", style="primary").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.save_folder, width=40).grid(row=2, column=1, padx=5, pady=5)

        ttkb.Label(self.main_tab, text="Camera width:", style="primary").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.camera_width, width=40).grid(row=3, column=1, padx=5, pady=5)

        ttkb.Label(self.main_tab, text="Camera height:", style="primary").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.camera_height, width=40).grid(row=4, column=1, padx=5, pady=5)

        ttkb.Label(self.main_tab, text="Camera URL:", style="primary").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.camera_url, width=40).grid(row=5, column=1, padx=5, pady=5)

        # Test key input field
        ttkb.Label(self.main_tab, text="Test screenshot key:", style="primary").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Entry(self.main_tab, textvariable=self.test_key, width=5).grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        # Checkbox for keyboard capture
        ttkb.Checkbutton(self.main_tab, text="Screenshot by key", variable=self.enable_keyboard_capture, style="round-toggle").grid(row=7,
                                                                                                             column=0,
                                                                                                             columnspan=2,
                                                                                                             padx=5,
                                                                                                             pady=5,
                                                                                                             sticky=tk.W)

        # Control buttons
        ttkb.Button(self.main_tab, text="Start", command=self.start, style="success").grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)
        ttkb.Button(self.main_tab, text="Stop", command=self.stop, style="danger").grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)
        ttkb.Button(self.main_tab, text="Check Camera", command=self.check_camera, style="info").grid(row=9, column=0,
                                                                                           columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Terminal window for messages
        self.terminal = scrolledtext.ScrolledText(self.main_tab, wrap=tk.WORD, width=80, height=20, bg="#1e1e1e", fg="white")
        self.terminal.grid(row=10, column=0, columnspan=2, padx=5, pady=5)

        # Widget for camera image display
        self.image_label = ttkb.Label(self.main_tab)
        self.image_label.grid(row=11, column=0, columnspan=2, padx=5, pady=5)

    def create_settings_tab(self):
        # Save settings button
        ttkb.Button(self.settings_tab, text="Save Settings", command=self.save_settings, style="primary").grid(
            row=0, column=0,
            padx=5, pady=5)

        # Theme selection
        ttkb.Label(self.settings_tab, text="Select theme:", style="primary").grid(row=1, column=0, padx=5, pady=5,
                                                                                  sticky=tk.W)
        theme_frame = ttkb.Frame(self.settings_tab)
        theme_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttkb.Radiobutton(theme_frame, text="Light", variable=self.theme, value="cosmo",
                         command=self.change_theme, style="success").pack(side=tk.LEFT)
        ttkb.Radiobutton(theme_frame, text="Dark", variable=self.theme, value="darkly", command=self.change_theme,
                         style="dark").pack(
            side=tk.LEFT)

    def start(self):
        global PORT, BAUDRATE, SAVE_FOLDER, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_HTTP_URL

        # Update settings
        PORT = self.port.get()
        BAUDRATE = self.baudrate.get()
        SAVE_FOLDER = self.save_folder.get()
        CAMERA_WIDTH = self.camera_width.get()
        CAMERA_HEIGHT = self.camera_height.get()
        CAMERA_HTTP_URL = self.camera_url.get()

        self.printer = connect_to_printer(PORT, BAUDRATE)
        if self.printer:
            self.stop_event.clear()
            threading.Thread(
                target=main,
                args=(self.printer, self.counter, self.test_counter, self.stop_event, self.enable_keyboard_capture,
                      self.test_key, self.terminal, self.image_label),
                daemon=True
            ).start()
            print("Program started.")

    def stop(self):
        self.stop_event.set()
        if self.printer and self.printer.is_open:
            self.printer.close()
        print("Program stopped.")

    def check_camera(self):
        threading.Thread(target=check_camera_thread, args=(self.camera_url.get(), self.terminal, self.image_label),
                         daemon=True).start()

    def save_settings(self):
        settings = {
            "port": self.port.get(),
            "baudrate": self.baudrate.get(),
            "save_folder": self.save_folder.get(),
            "camera_width": self.camera_width.get(),
            "camera_height": self.camera_height.get(),
            "camera_url": self.camera_url.get(),
            "test_key": self.test_key.get(),
            "theme": self.theme.get()
        }
        with open("settings.json", "w") as file:
            json.dump(settings, file)
        print("Settings saved.")

    def change_theme(self):
        theme = self.theme.get()
        # Use existing style, don't create new one
        self.root.style.theme_use(theme)

if __name__ == "__main__":
    root = ttkb.Window(themename=DEFAULT_THEME)
    app = App(root)
    root.mainloop()