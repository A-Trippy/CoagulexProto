import serial
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import cv2 as cv
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import time
from collections import deque

# Buffers for plotting
BUFFER_SIZE = 100
temps = deque(maxlen=BUFFER_SIZE)
temps2 = deque(maxlen=BUFFER_SIZE)
times = deque(maxlen=BUFFER_SIZE)

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
TEMP_THRESHOLD = 37.0

ready_to_track = False
lock = threading.Lock()

window = Tk()
window.title("Coagulex")
window.geometry("1400x900")
window.configure(background="#EEF7FF")

notebook = ttk.Notebook(window)
notebook.pack(fill='both', expand=True)

frame_graph = Frame(notebook, bg="#EEF7FF")
frame_video = Frame(notebook, bg="#EEF7FF")
notebook.add(frame_graph, text="Temperature Graph")
notebook.add(frame_video, text="Video Tracking")

# Graph Setup
fig = Figure(figsize=(6.4, 4.8), dpi=100)
ax = fig.add_subplot(111)
line1, = ax.plot([], [], '-', label="Temp 1 (°C)", color='tab:blue')
line2, = ax.plot([], [], '-', label="Temp 2 (°C)", color='tab:orange')
ax.set_title("Real-Time Temperature")
ax.set_xlabel("Time")
ax.set_ylabel("Temperature (°C)")
ax.grid(True)
ax.legend()
canvas = FigureCanvasTkAgg(fig, master=frame_graph)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(padx=10, pady=10)

current_temp_label = Label(frame_graph, text="Current Temperature in 1: -- °C\nCurrent Temperature in 2: -- °C", font=("Times New Roman", 14), bg="#EEF7FF")
current_temp_label.pack(pady=5)

# Video Feed Setup
video_label = Label(frame_video)
video_label.pack(padx=10, pady=10)

distance_label = Label(frame_video, text="Total Distance Moved: 0.00 px", font=("Times New Roman", 14), bg="#EEF7FF")
distance_label.pack(pady=5)

vidCap = cv.VideoCapture(0)
if not vidCap.isOpened():
    print("Could not open webcam.")
    exit()

def parse_serial_line(line):
    parts = line.split()
    t1 = next(part.split(":")[1] for part in parts if part.startswith("T1:"))
    t2 = next(part.split(":")[1] for part in parts if part.startswith("T2:"))
    return float(t1), float(t2)

def serial_reader():
    global ready_to_track
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            print("Serial:", line)
            try:
                t1, t2 = parse_serial_line(line)
                with lock:
                    current_time = datetime.now()
                    temps.append(t1)
                    temps2.append(t2)
                    times.append(current_time)
                    if t1 >= TEMP_THRESHOLD:
                        ready_to_track = True
            except Exception as e:
                print(f"Parsing error: {e}")

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

# Contour tracking vars
tracked_contour = None
last_drawn_contour = None
last_drawn_center = None
last_contour_update_time = time.time()
prev_center = None
total_distance = 0
tracking_locked = False

CONTOUR_UPDATE_INTERVAL = 0.3
DISTANCE_THRESHOLD = 2.5

def get_center(contour):
    x, y, w, h = cv.boundingRect(contour)
    return (x + w // 2, y + h // 2)

def contours_similar(c1, c2, pos_thresh=50, area_thresh=0.3):
    cx1, cy1 = get_center(c1)
    cx2, cy2 = get_center(c2)
    pos_dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
    a1 = cv.contourArea(c1)
    a2 = cv.contourArea(c2)
    area_ratio = min(a1, a2) / max(a1, a2) if max(a1, a2) > 0 else 0
    return pos_dist < pos_thresh and area_ratio > (1 - area_thresh)

def update_video():
    global tracked_contour, last_drawn_contour, last_drawn_center
    global last_contour_update_time, prev_center, total_distance
    global tracking_locked

    ret, frame = vidCap.read()
    if not ret:
        window.after(10, update_video)
        return

    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blurred, 100, 200)
    contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    current_contour = None
    if contours:
        if not tracking_locked:
            tracked_contour = max(contours, key=cv.contourArea)
            tracking_locked = True
            current_contour = tracked_contour
        else:
            for contour in contours:
                if contours_similar(tracked_contour, contour):
                    current_contour = contour
                    tracked_contour = contour
                    break

    current_time = time.time()
    update = False

    if current_contour is not None and (current_time - last_contour_update_time) >= CONTOUR_UPDATE_INTERVAL:
        current_center = get_center(current_contour)
        if last_drawn_center is None:
            update = True
        else:
            dx = current_center[0] - last_drawn_center[0]
            dy = current_center[1] - last_drawn_center[1]
            dist_moved = np.sqrt(dx**2 + dy**2)
            update = dist_moved >= DISTANCE_THRESHOLD

        if update:
            last_drawn_contour = current_contour
            last_drawn_center = current_center
            if prev_center is not None:
                dy_total = last_drawn_center[1] - prev_center[1]
                total_distance += abs(dy_total)
                distance_label.config(text=f"Total Distance Moved: {total_distance:.2f} px")
            prev_center = last_drawn_center
            last_contour_update_time = current_time

    if last_drawn_contour is not None and last_drawn_center is not None:
        cv.drawContours(frame, [last_drawn_contour], -1, (0, 255, 0), 2)
        cv.circle(frame, last_drawn_center, 5, (0, 0, 255), -1)

    cv.putText(frame, f"Total Moved: {total_distance:.2f}px", (10, 30),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)
    window.after(30, update_video)

threading.Thread(target=serial_reader, daemon=True).start()
update_plot()
update_video()
window.mainloop()
