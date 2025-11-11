import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Label, Frame
from PIL import Image, ImageTk
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import time
import os

# Simulated data source
data_queue = []

def simulate_serial():
    while True:
        time.sleep(0.1)
        data_queue.append(random.randint(20, 40))

# Main GUI Class
class CoagulexApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coagulex - Real-Time Temperature Monitor")
        self.root.state('zoomed')  # Fullscreen

        # Premium theme styling
        self.style = Style(theme="darkly")  # "darkly" has a glossy premium look
        self.root.configure(bg=self.style.colors.bg)

        self.setup_ui()
        self.x_data, self.y_data = [], []
        self.start_plot_update()

    def setup_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)

        # Graph frame
        graph_frame = Frame(self.root, bootstyle="dark", padding=20)
        graph_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        fig = Figure(figsize=(8, 5), dpi=100, facecolor='#202020')
        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor('#1c1c1c')
        self.ax.tick_params(colors='white')
        self.ax.spines[:].set_color('white')
        self.ax.set_title("Real-Time Temperature", color='white', fontsize=14)
        self.ax.set_xlabel("Time", color='white')
        self.ax.set_ylabel("Temperature (°C)", color='white')
        self.line, = self.ax.plot([], [], color="#0ff", linewidth=2)

        self.canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        # Side info frame
        side_frame = Frame(self.root, bootstyle="dark", padding=(20, 30))
        side_frame.grid(row=0, column=1, sticky="n", padx=(10, 20), pady=20)

        # Icon
        try:
            img = Image.open("C:\Python\CoagulexInvert.png").resize((225, 125))

            

            self.icon = ImageTk.PhotoImage(img)
            icon_label = tk.Label(side_frame, image=self.icon, bg=self.style.colors.bg)
            icon_label.pack(pady=(0, 20))
        except:
            pass

        # Temperature Labels
        Label(side_frame, text="Current Temperature:", bootstyle="info", font=("Segoe UI", 12)).pack(anchor="w")
        self.temp_val = Label(side_frame, text="-- °C", font=("Segoe UI", 16, "bold"), bootstyle="light")
        self.temp_val.pack(anchor="w", pady=(0, 20))

        # Control Buttons
        btn_frame = Frame(side_frame, bootstyle="dark")
        btn_frame.pack(pady=30)

        self.start_btn = Button(btn_frame, text="Start", command=self.toggle_start, bootstyle="success-outline", width=10)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.reset_btn = Button(btn_frame, text="Reset", command=self.reset_data, bootstyle="warning-outline", width=10)
        self.reset_btn.grid(row=0, column=1, padx=5)

        self.save_btn = Button(btn_frame, text="Save", command=self.save_data, bootstyle="info-outline", width=10)
        self.save_btn.grid(row=0, column=2, padx=5)

    def toggle_start(self):
        if not hasattr(self, 'running') or not self.running:
            self.running = True
            self.start_btn.config(text="Pause", bootstyle="danger-outline")
        else:
            self.running = False
            self.start_btn.config(text="Start", bootstyle="success-outline")

    def reset_data(self):
        self.x_data, self.y_data = [], []
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
        self.temp_val.config(text="-- °C")

    def save_data(self):
        with open("temperature_log.csv", "w") as f:
            f.write("Time,Temperature\n")
            for x, y in zip(self.x_data, self.y_data):
                f.write(f"{x},{y}\n")

    def start_plot_update(self):
        if hasattr(self, 'running') and self.running and data_queue:
            temp = data_queue.pop(0)
            self.y_data.append(temp)
            self.x_data.append(len(self.x_data))
            self.line.set_data(self.x_data, self.y_data)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
            self.temp_val.config(text=f"{temp:.2f} °C")
        self.root.after(100, self.start_plot_update)


# Launch GUI
if __name__ == '__main__':
    threading.Thread(target=simulate_serial, daemon=True).start()
    root = tk.Tk()
    app = CoagulexApp(root)
    root.mainloop()
