import serial
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from datetime import datetime, timedelta
import numpy as np
import cv2 as cv
import time
from tkinter import *
from PIL import Image, ImageTk

#Serial and Plotting Configuration
SERIAL_PORT = 'COM3'  # Change as needed
BAUD_RATE = 115200
TEMP_THRESHOLD = 37.0
MAX_POINTS = 100

#Ex. Serial output: Rig 1 Resistance = 109.58648681 Rig 2 Resistance = 114.29748535         T1:24.62 T2:36.78       100.0000 23.4009

temps = []
temps2 = []
times = []
ready_to_track = False
lock = threading.Lock()

#Serial thread to read temperature
def serial_reader():
    global ready_to_track
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            print("Serial:", line)

            t1, t2, distance, displacement = parse_serial_line(line)

            if t1 is not None:
                with lock:
                    if t1 >= TEMP_THRESHOLD:
                        ready_to_track = True

def parse_serial_line(line):
    try:
        if "T1" in line and "T2" in line:
            parts = line.strip().split()
            t1 = float(parts[6].split(":")[1])
            t2 = float(parts[7].split(":")[1])
            distance = float(parts[8])
            displacement = float(parts[9])
            times.append(datetime.now())
            temps.append(t1)
            temps2.append(t2)
            return t1, t2, distance, displacement
    except Exception as e:
        print(f"[Parse Error]: {e}")
    return None, None, None, None

#Setup plot
fig, ax = plt.subplots()
line1, = ax.plot([], [], '-', label="T1 (°C)", color='tab:blue')
line2, = ax.plot([], [], '-', label="T2 (°C)", color='tab:orange')
ax.set_title("Real-Time Temperature")
ax.set_xlabel("Time")
ax.set_ylabel("Temperature")
ax.grid(True)
ax.legend()
plt.tight_layout()

import matplotlib.dates as mdates
from datetime import timedelta

#GUI Setup
window = Tk()
window.geometry("1400x700")
window.title("Coagulex")
window.configure(background="#012A53")

img = Image.open("C:\Python\CoagulexInvert.png")
icon = ImageTk.PhotoImage(img)
window.iconphoto(True, icon)

#Matplotlib Figure
fig = Figure(figsize=(6, 5), dpi=100)
ax = fig.add_subplot(111)
line, = ax.plot([], [], 'r-')  # Line to be updated

x_data, y_data = [], []

canvas = FigureCanvasTkAgg(fig, master=window)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=0, column=0, padx=10, pady=10, sticky="nw")


def update_plot(frame):
    with lock:
        if not times or not temps:
            return line1, line2

        # Update line data
        line1.set_data(times, temps)
        line2.set_data(times, temps2)
        

        # Y axis: fixed range a bit wider than expected temps
        ax.set_ylim(5, 45)

        # X axis: dynamic range, last 2 minutes or full range if less data
        max_time = times[-1]
        min_time = max_time - timedelta(seconds=120)

        if times[0] > min_time:
            # Not enough data for full 2 minutes, show all data
            ax.set_xlim(times[0], max_time)
        else:
            ax.set_xlim(min_time, max_time)

        # Format datetime ticks nicely
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()

        ax.relim()
        ax.autoscale_view()  # autoscale in y is overridden by set_ylim above
        canvas.draw()
    return line1, line2

anim = animation.FuncAnimation(fig, update_plot, interval=500)

#Start serial reading thread
serial_thread = threading.Thread(target=serial_reader, daemon=True)
serial_thread.start()

# Start the matplotlib plot in a non-blocking way
plt.show(block=False)

#Open webcam
vidCap = cv.VideoCapture(0)
if not vidCap.isOpened(): # Check if the video capture opened successfully
    print("Error: Could not open video.")
    exit()

prev_center = None
total_distance = 0
tracked_contour = None
missing_frames = 0
max_missing_frames = 8

def get_center(contour):
    x, y, w, h = cv.boundingRect(contour)
    return (x + w // 2, y + h // 2)

def contours_similar(c1, c2, pos_thresh=50, area_thresh=0.3):
    # Check similarity by position and area
    cx1, cy1 = get_center(c1)
    cx2, cy2 = get_center(c2)
    pos_dist = np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)

    a1 = cv.contourArea(c1)
    a2 = cv.contourArea(c2)
    area_ratio = min(a1, a2) / max(a1, a2) if max(a1, a2) > 0 else 0

    return pos_dist < pos_thresh and area_ratio > (1 - area_thresh)

frame_counter = 0
process_every = 5  # Process every 5th frame

import time
import numpy as np
import cv2 as cv

# Assume tracked_contour, contours_similar(), get_center() etc. are defined as before

CONTOUR_UPDATE_INTERVAL = 0.3  # seconds
DISTANCE_THRESHOLD = 3.5       # pixels

last_drawn_contour = None
last_drawn_center = None
last_contour_update_time = time.time()
prev_center = None
total_distance = 0

while True:
    ret, frame = vidCap.read()
    if not ret:
        break

    # Preprocessing for contour detection
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blurred, 100, 200)
    contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    current_contour = None

    if contours:
        if tracked_contour is None:
            tracked_contour = max(contours, key=cv.contourArea)
            current_contour = tracked_contour
        else:
            for contour in contours:
                if contours_similar(tracked_contour, contour):
                    current_contour = contour
                    tracked_contour = contour
                    break

    current_time = time.time()
    update = False
    # Update contour and center only every 1.5 seconds AND if moved ≥ 4 pixels
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
                dx_total = last_drawn_center[0] - prev_center[0]
                dy_total = last_drawn_center[1] - prev_center[1]
                dist = np.sqrt(dx_total ** 2 + dy_total ** 2)
                total_distance += dist
            prev_center = last_drawn_center
            last_contour_update_time = current_time

    # Draw the last updated contour and center on every frame
    if last_drawn_contour is not None and last_drawn_center is not None:
        cv.drawContours(frame, [last_drawn_contour], -1, (0, 255, 0), 2)
        cv.circle(frame, last_drawn_center, 5, (0, 0, 255), -1)

    # Show distance info using total_distance and the last movement distance (if updated)
    cv.putText(frame, f"Total Moved: {total_distance:.2f}px", (10, 30),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Optional: display distance since last update if available
    '''if last_drawn_center is not None and prev_center is not None:
        dx = last_drawn_center[0] - prev_center[0]
        dy = last_drawn_center[1] - prev_center[1]
        dist_since_last = np.sqrt(dx**2 + dy**2)
        cv.putText(frame, f"Moved since update: {dist_since_last:.2f}px", (10, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)'''

    # Convert grayscale back to BGR so contours and colored text can be drawn
    gray_bgr = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)

    # Draw the last updated contour and center on every frame
    if last_drawn_contour is not None and last_drawn_center is not None:
        cv.drawContours(gray_bgr, [last_drawn_contour], -1, (0, 255, 0), 2)
        cv.circle(gray_bgr, last_drawn_center, 5, (0, 0, 255), -1)

    # Show distance info on the black-and-white frame
    cv.putText(gray_bgr, f"Total Moved: {total_distance:.2f}px", (10, 30),
            cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv.imshow("Tracking", gray_bgr)


    if cv.waitKey(1) & 0xFF == ord('q'):
        break

vidCap.release()
cv.destroyAllWindows()

print("Total distance traveled:", total_distance)

# Start mainloop
window.mainloop()