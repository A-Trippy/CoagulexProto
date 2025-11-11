# Full integration of premium UI with tracking, plotting, and serial logic

import serial
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import cv2 as cv
from PIL import Image, ImageTk
import time
from collections import deque
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# === Constants and Buffers === #
SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
TEMP_THRESHOLD = 37.0
BUFFER_SIZE = 100

temps = deque(maxlen=BUFFER_SIZE)
temps2 = deque(maxlen=BUFFER_SIZE)
times = deque(maxlen=BUFFER_SIZE)
lock = threading.Lock()
ready_to_track = False

# === GUI Setup === #
app = ttk.Window(themename="cyborg")
app.title("Coagulex - Advanced Temperature & Motion Monitor")
app.geometry("1440x800")

main_frame = ttk.Frame(app)
main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# === Temperature Plot === #
plot_frame = ttk.LabelFrame(main_frame, text="Real-Time Temperature Monitoring")
plot_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

fig = Figure(figsize=(6, 4), dpi=100)
ax = fig.add_subplot(111)
line1, = ax.plot([], [], '-', label="Sensor 1 (°C)", color='cyan')
line2, = ax.plot([], [], '-', label="Sensor 2 (°C)", color='salmon')
ax.set_xlabel("Time")
ax.set_ylabel("Temperature (°C)")
ax.grid(True)
ax.legend()

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=BOTH, expand=True)

# === Video Display === #
video_frame = ttk.LabelFrame(main_frame, text="Live Motion Tracking")
video_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

video_label = ttk.Label(video_frame)
video_label.pack(fill=BOTH, expand=True)

# === Status Panel === #
status_frame = ttk.Frame(main_frame)
status_frame.grid(row=0, column=2, sticky="n")

current_temp_label = ttk.Label(status_frame, text="Temperature S1: -- °C\nTemperature S2: -- °C", font=("Segoe UI", 12))
current_temp_label.pack(pady=10)

distance_label = ttk.Label(status_frame, text="Motion Distance: 0.00 px", font=("Segoe UI", 12))
distance_label.pack(pady=10)

# === Control Buttons === #
btn_frame = ttk.Frame(status_frame)
btn_frame.pack(pady=10)

ttk.Button(btn_frame, text="Pause Monitor", bootstyle="warning-outline").pack(fill=X, pady=5)
ttk.Button(btn_frame, text="Reset Data", bootstyle="danger-outline").pack(fill=X, pady=5)
ttk.Button(btn_frame, text="Save Log", bootstyle="success-outline").pack(fill=X, pady=5)

# === Serial Reader === #
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

# === Plot Update === #
def update_plot():
    with lock:
        if not times:
            app.after(500, update_plot)
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

        current_temp_label.config(text=f"Temperature S1: {temps[-1]:.2f} °C\nTemperature S2: {temps2[-1]:.2f} °C")

    app.after(500, update_plot)

# === Camera Setup & Tracking === #
vidCap1 = cv.VideoCapture(0)
vidCap2 = cv.VideoCapture(1)

# Tracking state variables
tracked_contour = None
last_drawn_contour = None
last_drawn_center = None
prev_center = None
total_distance = 0
tracking_locked = False
CONTOUR_UPDATE_INTERVAL = 0.3
DISTANCE_THRESHOLD = 2.5
last_contour_update_time = time.time()

def get_center(contour):
    x, y, w, h = cv.boundingRect(contour)
    return (x + w // 2, y + h // 2)

def contours_similar(c1, c2):
    cx1, cy1 = get_center(c1)
    cx2, cy2 = get_center(c2)
    pos_dist = np.hypot(cx1 - cx2, cy1 - cy2)
    area_ratio = min(cv.contourArea(c1), cv.contourArea(c2)) / max(cv.contourArea(c1), cv.contourArea(c2))
    return pos_dist < 50 and area_ratio > 0.7

def update_video():
    global tracked_contour, last_drawn_contour, last_drawn_center, prev_center, total_distance, tracking_locked, last_contour_update_time

    ret, frame = vidCap1.read()
    if not ret:
        app.after(30, update_video)
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
        else:
            for contour in contours:
                if contours_similar(tracked_contour, contour):
                    tracked_contour = contour
                    break

    current_time = time.time()
    if tracked_contour is not None and (current_time - last_contour_update_time) >= CONTOUR_UPDATE_INTERVAL:
        current_center = get_center(tracked_contour)
        if last_drawn_center is None or np.linalg.norm(np.subtract(current_center, last_drawn_center)) >= DISTANCE_THRESHOLD:
            if last_drawn_center:
                total_distance += abs(current_center[1] - last_drawn_center[1])
            last_drawn_center = current_center
            last_drawn_contour = tracked_contour
            prev_center = last_drawn_center
            last_contour_update_time = current_time

    if last_drawn_contour is not None and last_drawn_center is not None:
        cv.drawContours(frame, [last_drawn_contour], -1, (0, 255, 0), 2)
        cv.circle(frame, last_drawn_center, 5, (0, 0, 255), -1)

    distance_label.config(text=f"Motion Distance: {total_distance:.2f} px")
    frame = cv.resize(frame, (640, 480))
    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    imgtk = ImageTk.PhotoImage(image=Image.fromarray(rgb))
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    app.after(30, update_video)

# === Start Threads and Mainloop === #
threading.Thread(target=serial_reader, daemon=True).start()
update_plot()
update_video()
app.mainloop()
