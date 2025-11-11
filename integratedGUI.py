#This is the best version of the edge detection and contour tracking

import serial
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import cv2 as cv
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk
import time
from collections import deque
import ttkbootstrap as ttk
from ttkbootstrap import Style
from ttkbootstrap.constants import *

# Buffers to hold recent values (rolling plot)
BUFFER_SIZE = 100
temps = deque(maxlen=BUFFER_SIZE)
temps2 = deque(maxlen=BUFFER_SIZE)
times = deque(maxlen=BUFFER_SIZE)


#Serial & Plot Setup
SERIAL_PORT = 'COM3'  # Adjust to your COM port
BAUD_RATE = 115200
TEMP_THRESHOLD = 37.0

#Ex. Serial: Rig 1 Resistance = 109.58648681 Rig 2 Resistance = 114.29748535         T1:24.62 T2:36.78       100.0000 23.4009

ready_to_track = False
lock = threading.Lock()

#GUI Setup
window = Tk()
window.grid_columnconfigure(0, weight=1)
window.grid_columnconfigure(1, weight=1)

window.geometry("1400x700")
window.title("Coagulex")
window.configure(background="#A6B8C7")

# Load icon (optional)
try:
    img = Image.open("C:/Python/Pfp.jpg")
    icon = ImageTk.PhotoImage(img)
    window.iconphoto(True, icon)
except:
    print("Icon load failed (check path)")

#Matplotlib Graph Setup
fig = Figure(figsize=(6.4, 4.8), dpi=100)  # 6.4*100 = 640 px, 4.8*100 = 480 px

ax = fig.add_subplot(111)
line1, = ax.plot([], [], '-', label="Temp 1 (°C)", color='tab:blue')
line2, = ax.plot([], [], '-', label="Temp 2 (°C)", color='tab:orange')
ax.set_title("Real-Time Temperature")
ax.set_xlabel("Time")
ax.set_ylabel("Temperature (°C)")
ax.grid(True)
ax.legend()

canvas = FigureCanvasTkAgg(fig, master=window)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

#Video Feed Setup
video_label = Label(window)
video_label.grid(row=0, column=1, padx=10, pady=10)

vidCap = cv.VideoCapture(0)
if not vidCap.isOpened():
    print("Could not open webcam.")
    exit()

#Serial Thread
def parse_serial_line(line):
    
    # Split string into parts
    parts = line.split()

    # Extract values after T1: and T2:
    t1 = next(part.split(":")[1] for part in parts if part.startswith("T1:"))
    t2 = next(part.split(":")[1] for part in parts if part.startswith("T2:"))

    return float(t1), float(t2), None, None

def serial_reader():
    global ready_to_track
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            print("Serial:", line)
            try:
                t1, t2, _, _ = parse_serial_line(line)
                with lock:
                    current_time = datetime.now()
                    temps.append(t1)
                    temps2.append(t2)
                    times.append(current_time)

                    if t1 >= TEMP_THRESHOLD:
                        ready_to_track = True
            except Exception as e:
                print(f"Parsing error: {e}")

#Plot Update
def update_plot():
    with lock:
        if not times:
            window.after(500, update_plot)
            return

        line1.set_data(times, temps)
        line2.set_data(times, temps2)
        ax.set_ylim(5, 45)

        max_time = times[-1]
        min_time = max_time - timedelta(seconds=30)
        ax.set_xlim(min_time, max_time)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        fig.autofmt_xdate()
        ax.relim()
        ax.autoscale_view(scaley=True)
        canvas.draw()

        if temps and temps2:
            current_temp_label.config(
                text=f"Current Temperature in 1: {temps[-1]:.2f} °C | "
                     f"Current Temperature in 2: {temps2[-1]:.2f} °C")

    window.after(500, update_plot)

#Contour Tracking
tracked_contour = None
last_drawn_contour = None
last_drawn_center = None
last_contour_update_time = time.time()
prev_center = None
total_distance = 0
tracking_locked = False

CONTOUR_UPDATE_INTERVAL = 0.3  # seconds
DISTANCE_THRESHOLD = 2.5      # pixels

def get_center(contour):
    x, y, w, h = cv.boundingRect(contour)
    return (x + w // 2, y + h // 2)

def contours_similar(c1, c2, pos_thresh=50, area_thresh=0.3):
    cx1, cy1 = get_center(c1)
    cx2, cy2 = get_center(c2)
    pos_dist = np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)
    a1 = cv.contourArea(c1)
    a2 = cv.contourArea(c2)
    area_ratio = min(a1, a2) / max(a1, a2) if max(a1, a2) > 0 else 0
    return pos_dist < pos_thresh and area_ratio > (1 - area_thresh)

def update_video():
    global tracked_contour, last_drawn_contour, last_drawn_center
    global last_contour_update_time, prev_center, total_distance
    global tracking_locked  # Flag to indicate if tracking is locked

    ... # Read the next frame from the video capture

    ret, frame = vidCap.read()
    if not ret:
        window.after(10, update_video)
        return
    
    #Preprocessing for contour detection
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blurred, 100, 200)
    contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)


    current_contour = None
    
    if contours:
        if not tracking_locked:
            # Lock onto the largest initial contour
            tracked_contour = max(contours, key=cv.contourArea)
            tracking_locked = True
            current_contour = tracked_contour
        else:
            # Only update if a similar contour is found (likely same object)
            for contour in contours:
                if contours_similar(tracked_contour, contour):
                    current_contour = contour
                    tracked_contour = contour
                    break


    current_time = time.time()
    update = False

     # Update contour and center only every 0.3 seconds AND if moved ≥ 2.5 pixels
    if current_contour is not None and (current_time - last_contour_update_time) >= CONTOUR_UPDATE_INTERVAL:
        current_center = get_center(current_contour)
        if last_drawn_center is None:
            # First update ever
            update = True
        else:
            dx = current_center[0] - last_drawn_center[0]
            dy = current_center[1] - last_drawn_center[1]
            dist_moved = np.sqrt(dx ** 2 + dy ** 2)
            update = dist_moved >= DISTANCE_THRESHOLD

        if update:
        # Update the contour and center used for drawing
            last_drawn_contour = current_contour
            last_drawn_center = current_center

            # Update distance traveled total
            if prev_center is not None:
                dy_total = last_drawn_center[1] - prev_center[1]
                total_distance += abs(dy_total)

                # Update the distance moved label
                distance_label.config(text=f"Total Distance Moved: {total_distance:.2f} px")

            prev_center = last_drawn_center
            last_contour_update_time = current_time

    # Draw the last updated contour and center on every frame
    if last_drawn_contour is not None and last_drawn_center is not None:
        cv.drawContours(frame, [last_drawn_contour], -1, (0, 255, 0), 2)
        cv.circle(frame, last_drawn_center, 5, (0, 0, 255), -1)

    # Show distance info using total_distance and the last movement distance (if updated)
    cv.putText(frame, f"Total Moved: {total_distance:.2f}px", (10, 30),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Convert to Tkinter Image
    frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    frame = cv.resize(frame, (640, 480))
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

    window.after(30, update_video)

#Make the GUI look nice
window.configure(background="#EEF7FF")
# Add a subtitle label
#subtitle_label = Label(window, text="Monitoring Temperature and Object Movement", font=("Arial", 16), bg="#EEF7FF")
#subtitle_label.grid(row=1, column=0, columnspan=2, pady=5)

# Labels for current temperature and distance moved
current_temp_label = Label(window, text="Current Temperature in 1: -- °C \n Current Temperature in 2: -- °C", font=("Times New Roman", 14), bg="#EEF7FF")
current_temp_label.grid(row=3, column=0, columnspan=2, pady=5)

distance_label = Label(window, text="Total Distance Moved: 0.00 px", font=("Times New Roman", 14), bg="#EEF7FF")
distance_label.grid(row=4, column=0, columnspan=2, pady=5)



# Add a footer label
#footer_label = Label(window, text="Developed by Your Name", font=("Arial", 12), bg="#EEF7FF")
#footer_label.grid(row=2, column=0, columnspan=2, pady=10)
# Start the serial reader thread


#Launch Everything
# Start threads and updates
threading.Thread(target=serial_reader, daemon=True).start()
update_video()
update_plot()
window.mainloop()