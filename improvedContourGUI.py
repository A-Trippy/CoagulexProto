
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

class CoagulexApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coagulex - Advanced Temperature & Motion Monitor")
        self.root.state('zoomed')  # Fullscreen

        # Premium theme styling
        self.style = Style(theme="darkly")  # Premium dark theme
        self.root.configure(bg=self.style.colors.bg)

        # Data buffers
        self.BUFFER_SIZE = 100
        self.temps = deque(maxlen=self.BUFFER_SIZE)
        self.temps2 = deque(maxlen=self.BUFFER_SIZE)
        self.times = deque(maxlen=self.BUFFER_SIZE)

        # Serial & tracking parameters
        self.SERIAL_PORT = 'COM3'
        self.BAUD_RATE = 115200
        self.TEMP_THRESHOLD = 37.0
        self.ready_to_track = False
        self.lock = threading.Lock()

        # Control states
        self.running = True
        self.monitoring_active = True

        # Video and tracking variables
        self.tracked_contour = None
        self.last_drawn_contour = None
        self.last_drawn_center = None
        self.last_contour_update_time = time.time()
        self.prev_center = None
        self.total_distance = 0
        self.tracking_locked = False
        self.CONTOUR_UPDATE_INTERVAL = 0.3
        self.DISTANCE_THRESHOLD = 2.5

        self.setup_ui()
        self.setup_video()
        self.start_serial_monitoring()
        self.start_updates()

    def setup_ui(self):
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=2)  # Graph area
        self.root.grid_columnconfigure(1, weight=2)  # Video area
        self.root.grid_columnconfigure(2, weight=1)  # Control panel

        # Graph frame
        self.setup_graph_frame()

        # Video frame  
        self.setup_video_frame()

        # Control panel
        self.setup_control_panel()

    def setup_graph_frame(self):
        graph_frame = ttk.Frame(self.root, bootstyle="dark", padding=15)
        graph_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        # Create matplotlib figure with dark theme
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor='#202020')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1c1c1c')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('white')
        self.ax.set_title("Real-Time Temperature Monitoring", color='white', fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Time", color='white')
        self.ax.set_ylabel("Temperature (°C)", color='white')
        self.ax.grid(True, alpha=0.3)

        # Temperature lines
        self.line1, = self.ax.plot([], [], '-', label="Sensor 1 (°C)", color='#00ffff', linewidth=2)
        self.line2, = self.ax.plot([], [], '-', label="Sensor 2 (°C)", color='#ff6b6b', linewidth=2)
        self.ax.legend(facecolor='#2c2c2c', edgecolor='white', labelcolor='white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

    def setup_video_frame(self):
        video_frame = ttk.Frame(self.root, bootstyle="dark", padding=15)
        video_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=20)

        # Video title
        ttk.Label(video_frame, text="Live Motion Tracking", 
                 bootstyle="info", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Video display
        self.video_label = ttk.Label(video_frame, background='#1c1c1c')
        self.video_label.pack(fill="both", expand=True)

    def setup_control_panel(self):
        control_frame = ttk.Frame(self.root, bootstyle="dark", padding=(20, 30))
        control_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 20), pady=20)

        # Logo/Icon section
        try:
            img = Image.open("C:/Python/CoagulexInvert.png").resize((100, 50))
            self.icon = ImageTk.PhotoImage(img)
            icon_label = ttk.Label(control_frame, image=self.icon, background=self.style.colors.bg)
            icon_label.pack(pady=(0, 20))
        except:
            # Fallback title if no icon
            ttk.Label(control_frame, text="COAGULEX", 
                     font=("Segoe UI", 20, "bold"), bootstyle="primary").pack(pady=(0, 20))

        # Status section
        status_frame = ttk.LabelFrame(control_frame, text="System Status", bootstyle="info", padding=15)
        status_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(status_frame, text="Temperature Sensor 1:", bootstyle="light", 
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.temp1_val = ttk.Label(status_frame, text="-- °C", font=("Segoe UI", 14, "bold"), 
                                  bootstyle="success")
        self.temp1_val.pack(anchor="w", pady=(0, 10))

        ttk.Label(status_frame, text="Temperature Sensor 2:", bootstyle="light", 
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.temp2_val = ttk.Label(status_frame, text="-- °C", font=("Segoe UI", 14, "bold"), 
                                  bootstyle="warning")
        self.temp2_val.pack(anchor="w", pady=(0, 10))

        ttk.Label(status_frame, text="Motion Distance:", bootstyle="light", 
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.distance_val = ttk.Label(status_frame, text="0.00 px", font=("Segoe UI", 12, "bold"), 
                                     bootstyle="info")
        self.distance_val.pack(anchor="w")

        # Control buttons
        control_buttons = ttk.LabelFrame(control_frame, text="Controls", bootstyle="primary", padding=15)
        control_buttons.pack(fill="x", pady=(0, 20))

        self.start_btn = ttk.Button(control_buttons, text="Pause Monitoring", 
                                   command=self.toggle_monitoring, bootstyle="warning", width=15)
        self.start_btn.pack(pady=5, fill="x")

        self.reset_btn = ttk.Button(control_buttons, text="Reset Data", 
                                   command=self.reset_data, bootstyle="danger-outline", width=15)
        self.reset_btn.pack(pady=5, fill="x")

        self.save_btn = ttk.Button(control_buttons, text="Save Log", 
                                  command=self.save_data, bootstyle="success-outline", width=15)
        self.save_btn.pack(pady=5, fill="x")

        # Threshold settings
        threshold_frame = ttk.LabelFrame(control_frame, text="Settings", bootstyle="secondary", padding=15)
        threshold_frame.pack(fill="x")

        ttk.Label(threshold_frame, text="Temp Threshold (°C):", bootstyle="light").pack(anchor="w")
        self.threshold_var = tk.StringVar(value=str(self.TEMP_THRESHOLD))
        threshold_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_var, width=10)
        threshold_entry.pack(anchor="w", pady=(0, 10))

        '''ttk.Button(threshold_frame, text="Update Threshold", 
                  command=self.update_threshold, bootstyle="info-outline").pack(fill="x")'''

    def setup_video(self):
        self.vidCap = cv.VideoCapture(0)

        if not self.vidCap.isOpened():
            print("Warning: Could not open webcam.")

    def start_serial_monitoring(self):
        threading.Thread(target=self.serial_reader, daemon=True).start()

    def serial_reader(self):
        #global ready_to_track
        try:
            ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=1)
            while True:
                if ser.in_waiting:
                    line = ser.readline().decode(errors='ignore').strip()
                    print("Serial:", line)
                    try:
                        t1, t2 = self.parse_serial_line(line)
                        with self.lock:
                            current_time = datetime.now()
                            self.temps.append(t1)
                            self.temps2.append(t2)
                            self.times.append(current_time)

                            if t1 >= self.TEMP_THRESHOLD:
                                self.ready_to_track = True
                    except Exception as e:
                        print(f"Parsing error: {e}")
        except Exception as e:
            print(f"Serial connection error: {e}")
            # Use simulated data if serial fails
            self.simulate_data()

    def parse_serial_line(self, line):
        parts = line.split()
        t1 = next(part.split(":")[1] for part in parts if part.startswith("T1:"))
        t2 = next(part.split(":")[1] for part in parts if part.startswith("T2:"))
        return float(t1), float(t2)

    '''def simulate_data(self):
        """Fallback simulation if serial connection fails"""
        import random
        while True:
            time.sleep(0.5)
            if self.monitoring_active:
                with self.lock:
                    current_time = datetime.now()
                    t1 = random.uniform(20, 45)
                    t2 = random.uniform(22, 43)
                    self.temps.append(t1)
                    self.temps2.append(t2)
                    self.times.append(current_time)'''

    def start_updates(self):
        self.update_plot()
        self.update_video()

    def update_plot(self):
        if self.monitoring_active:
            with self.lock:
                if self.times:
                    self.line1.set_data(self.times, self.temps)
                    self.line2.set_data(self.times, self.temps2)
                    self.ax.set_ylim(5, 50)

                    max_time = self.times[-1]
                    min_time = max_time - timedelta(seconds=60)
                    self.ax.set_xlim(min_time, max_time)
                    self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

                    self.fig.autofmt_xdate()
                    self.ax.relim()
                    self.ax.autoscale_view(scaley=True)
                    self.canvas.draw()

                    # Update temperature displays
                    if self.temps and self.temps2:
                        self.temp1_val.config(text=f"{self.temps[-1]:.2f} °C")
                        self.temp2_val.config(text=f"{self.temps2[-1]:.2f} °C")

        self.root.after(500, self.update_plot)

    def update_video(self):
        if not hasattr(self, 'vidCap') or not self.vidCap.isOpened():
            self.root.after(30, self.update_video)
            return

        ret, frame = self.vidCap.read()
        if not ret:
            self.root.after(30, self.update_video)
            return

        if self.monitoring_active:
            frame = self.process_contours(frame)

        # Resize and convert for display
        frame = cv.resize(frame, (640, 480))
        frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.root.after(30, self.update_video)

    def process_contours(self, frame):
        # Contour detection and tracking logic
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        blurred = cv.GaussianBlur(gray, (5, 5), 0)
        edges = cv.Canny(blurred, 100, 200)
        contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        current_contour = None

        if contours:
            if not self.tracking_locked:
                # If not locked, find the largest contour
                self.tracked_contour = max(contours, key=cv.contourArea)
                self.tracking_locked = True
                current_contour = self.tracked_contour
            else:
                for contour in contours:
                    if self.contours_similar(self.tracked_contour, contour):
                        current_contour = contour
                        self.tracked_contour = contour
                        break

        current_time = time.time()
        update = False

        if current_contour is not None and (current_time - self.last_contour_update_time) >= self.CONTOUR_UPDATE_INTERVAL:
            current_center = self.get_center(current_contour)
            if self.last_drawn_center is None:
                # First update ever
                update = True
            else:
                # Check if the contour has moved significantly
                dx = current_center[0] - self.last_drawn_center[0]
                dy = current_center[1] - self.last_drawn_center[1]
                dist_moved = np.sqrt(dx ** 2 + dy ** 2)
                
                update = dist_moved >= self.DISTANCE_THRESHOLD

            if update:
                # Update the contour and center used for drawing
                self.last_drawn_contour = current_contour
                self.last_drawn_center = current_center

                # Update distance traveled total
                if self.prev_center is not None:
                    dy_total = self.last_drawn_center[1] - self.prev_center[1]
                    self.total_distance += abs(dy_total)

                # Update the distance moved label
                    self.distance_val.config(text=f"{self.total_distance:.2f} px")

                self.prev_center = self.last_drawn_center
                self.last_contour_update_time = current_time

        # Draw the last updated contour and center on every frame
        if self.last_drawn_contour is not None and self.last_drawn_center is not None:
            cv.drawContours(frame, [self.last_drawn_contour], -1, (0, 255, 0), 2)
            cv.circle(frame, self.last_drawn_center, 5, (0, 0, 255), -1)

        cv.putText(frame, f"Distance: {self.total_distance:.2f}px", (10, 30),
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return frame

    def get_center(self, contour):
        x, y, w, h = cv.boundingRect(contour)
        return (x + w // 2, y + h // 2)

    def contours_similar(self, c1, c2, pos_thresh=50, area_thresh=0.3):
        cx1, cy1 = self.get_center(c1)
        cx2, cy2 = self.get_center(c2)
        pos_dist = np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)
        a1 = cv.contourArea(c1)
        a2 = cv.contourArea(c2)
        area_ratio = min(a1, a2) / max(a1, a2) if max(a1, a2) > 0 else 0
        return pos_dist < pos_thresh and area_ratio > (1 - area_thresh)

    def toggle_monitoring(self):
        self.monitoring_active = not self.monitoring_active
        if self.monitoring_active:
            self.start_btn.config(text="Pause Monitoring", bootstyle="warning")
        else:
            self.start_btn.config(text="Resume Monitoring", bootstyle="success")

    def reset_data(self):
        with self.lock:
            self.temps.clear()
            self.temps2.clear()
            self.times.clear()
        self.total_distance = 0
        self.tracking_locked = False
        self.tracked_contour = None
        self.last_drawn_contour = None
        self.last_drawn_center = None
        self.prev_center = None
        self.distance_val.config(text="0.00 px")
        self.temp1_val.config(text="-- °C")
        self.temp2_val.config(text="-- °C")

    def save_data(self):
        with self.lock:
            if self.times and self.temps and self.temps2:
                filename = f"coagulex_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(filename, "w") as f:
                    f.write("Time,Temperature_1,Temperature_2,Distance_Moved\n")
                    for t, t1, t2 in zip(self.times, self.temps, self.temps2):
                        f.write(f"{t.strftime('%Y-%m-%d %H:%M:%S')},{t1:.2f},{t2:.2f},{self.total_distance:.2f}\n")
                print(f"Data saved to {filename}")

    '''def update_threshold(self):
        try:
            self.TEMP_THRESHOLD = float(self.threshold_var.get())
            print(f"Threshold updated to {self.TEMP_THRESHOLD}°C")
        except ValueError:
            print("Invalid threshold value")'''


# Launch the application
if __name__ == '__main__':
    root = tk.Tk()
    app = CoagulexApp(root)
    root.mainloop()