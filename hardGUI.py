import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Label, Frame, Progressbar, Meter
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageFilter
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import random
import time
import os
import numpy as np

# Simulated data source
data_queue = []

def simulate_serial():
    """Simulate real-time temperature data"""
    while True:
        time.sleep(0.1)
        # Add some realistic noise to the temperature data
        base_temp = 32
        noise = random.uniform(-2, 2)
        trend = 0.05 * (random.random() - 0.5)
        data_queue.append(base_temp + noise + trend)
        if len(data_queue) > 1000:  # Limit queue size
            data_queue.pop(0)

class CoagulexApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coagulex - Professional Temperature Monitor")
        self.root.state('zoomed')  # Fullscreen
        
        # Premium theme with custom colors
        self.style = Style(theme="superhero")  # Professional dark theme
        self.root.configure(bg='#1a1a1a')
        
        # Custom color palette for premium look
        self.colors = {
            'bg_primary': '#1a1a1a',
            'bg_secondary': '#2d2d2d',
            'bg_card': '#363636',
            'accent_blue': '#00bcd4',
            'accent_green': '#4caf50',
            'accent_orange': '#ff9800',
            'accent_red': '#f44336',
            'text_primary': '#ffffff',
            'text_secondary': '#b0b0b0',
            'border': '#404040'
        }
        
        self.setup_ui()
        self.x_data, self.y_data = [], []
        self.running = False
        self.paused = False
        self.start_plot_update()

    def create_logo_with_background(self, logo_path, size=(200, 125)):
        """Create logo with modern card-style background"""
        try:
            # Load and process the logo
            logo = Image.open(logo_path)
            
            # Convert to RGBA if not already
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Resize logo maintaining aspect ratio
            logo.thumbnail((size[0]-40, size[1]-40), Image.Resampling.LANCZOS)
            
            # Create a modern card background
            card_bg = Image.new('RGBA', size, (54, 54, 54, 255))  # Dark card background
            
            # Add subtle gradient effect
            for y in range(size[1]):
                for x in range(size[0]):
                    # Create subtle gradient
                    gradient_factor = 1 - (y / size[1]) * 0.1
                    current_pixel = card_bg.getpixel((x, y))
                    new_color = tuple(int(c * gradient_factor) for c in current_pixel[:3]) + (255,)
                    card_bg.putpixel((x, y), new_color)
            
            # Add subtle border
            border_color = (64, 64, 64, 255)
            for i in range(2):  # 2px border
                for x in range(size[0]):
                    card_bg.putpixel((x, i), border_color)
                    card_bg.putpixel((x, size[1]-1-i), border_color)
                for y in range(size[1]):
                    card_bg.putpixel((i, y), border_color)
                    card_bg.putpixel((size[0]-1-i, y), border_color)
            
            # Center the logo on the card
            logo_x = (size[0] - logo.width) // 2
            logo_y = (size[1] - logo.height) // 2
            
            # If logo is black, make it white for better contrast
            logo_array = np.array(logo)
            if logo_array[:,:,:3].mean() < 50:  # If logo is mostly dark
                # Invert the logo colors for better visibility
                logo_array[:,:,0] = 255 - logo_array[:,:,0]  # Invert R
                logo_array[:,:,1] = 255 - logo_array[:,:,1]  # Invert G  
                logo_array[:,:,2] = 255 - logo_array[:,:,2]  # Invert B
                logo = Image.fromarray(logo_array)
            
            # Paste logo onto card background
            card_bg.paste(logo, (logo_x, logo_y), logo)
            
            return ImageTk.PhotoImage(card_bg)
            
        except Exception as e:
            print(f"Error processing logo: {e}")
            # Create a fallback logo placeholder
            placeholder = Image.new('RGBA', size, (54, 54, 54, 255))
            return ImageTk.PhotoImage(placeholder)

    def create_modern_plot(self):
        """Create a modern, professional-looking plot"""
        # Create figure with custom styling
        fig = Figure(figsize=(10, 6), dpi=100, facecolor='#2d2d2d')
        self.ax = fig.add_subplot(111)
        
        # Modern plot styling
        self.ax.set_facecolor('#1a1a1a')
        self.ax.grid(True, alpha=0.3, color='#404040', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        # Styling the spines
        for spine in self.ax.spines.values():
            spine.set_color('#404040')
            spine.set_linewidth(1)
        
        # Modern color scheme for text
        self.ax.tick_params(colors='#b0b0b0', labelsize=10)
        self.ax.set_title("Real-Time Temperature Monitoring", 
                         color='#ffffff', fontsize=16, fontweight='bold', pad=20)
        self.ax.set_xlabel("Time (seconds)", color='#b0b0b0', fontsize=12)
        self.ax.set_ylabel("Temperature (°C)", color='#b0b0b0', fontsize=12)
        
        # Create the main line with modern styling
        self.line, = self.ax.plot([], [], color=self.colors['accent_blue'], 
                                 linewidth=2.5, alpha=0.9)
        
        # Add a subtle fill under the line
        self.fill = None
        
        return fig

    def setup_ui(self):
        """Setup the modern UI layout"""
        # Configure main grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)

        # Main graph frame with modern styling
        graph_frame = Frame(self.root, bootstyle="dark", padding=25)
        graph_frame.grid(row=0, column=0, sticky="nsew", padx=(25, 15), pady=25)
        
        # Create modern plot
        fig = self.create_modern_plot()
        self.canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        # Right panel with premium styling
        right_panel = Frame(self.root, bootstyle="dark", padding=(25, 30))
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(15, 25), pady=25)

        # Logo with modern card design
        logo_frame = Frame(right_panel, bootstyle="dark", padding=15)
        logo_frame.pack(fill="x", pady=(0, 25))
        
        # Load logo with modern background
        try:
            self.logo_image = self.create_logo_with_background(
                "C:\\Python\\CoagulexInvert.png", (200, 125)
            )
            logo_label = tk.Label(logo_frame, image=self.logo_image, 
                                bg=self.style.colors.bg)
            logo_label.pack()
        except Exception as e:
            # Fallback text logo
            logo_label = Label(logo_frame, text="COAGULEX", 
                             font=("Segoe UI", 18, "bold"), 
                             bootstyle="info")
            logo_label.pack()

        # Status indicators section
        status_frame = Frame(right_panel, bootstyle="dark", padding=20)
        status_frame.pack(fill="x", pady=(0, 20))
        
        # Temperature display with modern cards
        temp_card = Frame(status_frame, bootstyle="secondary", padding=15)
        temp_card.pack(fill="x", pady=(0, 15))
        
        Label(temp_card, text="Current Temperature", 
              bootstyle="light", font=("Segoe UI", 11)).pack(anchor="w")
        self.temp_val = Label(temp_card, text="-- °C", 
                             font=("Segoe UI", 20, "bold"), 
                             bootstyle="info")
        self.temp_val.pack(anchor="w", pady=(5, 0))

        # Status indicator
        status_card = Frame(status_frame, bootstyle="secondary", padding=15)
        status_card.pack(fill="x", pady=(0, 15))
        
        Label(status_card, text="System Status", 
              bootstyle="light", font=("Segoe UI", 11)).pack(anchor="w")
        self.status_label = Label(status_card, text="Ready", 
                                 font=("Segoe UI", 12, "bold"), 
                                 bootstyle="success")
        self.status_label.pack(anchor="w", pady=(5, 0))

        # Progress indicator for visual feedback
        progress_card = Frame(status_frame, bootstyle="secondary", padding=15)
        progress_card.pack(fill="x")
        
        Label(progress_card, text="Data Collection", 
              bootstyle="light", font=("Segoe UI", 11)).pack(anchor="w")
        self.progress = Progressbar(progress_card, bootstyle="info-striped", 
                                   mode="indeterminate", length=180)
        self.progress.pack(anchor="w", pady=(5, 0))

        # Control buttons with modern styling
        control_frame = Frame(right_panel, bootstyle="dark", padding=20)
        control_frame.pack(fill="x", pady=(10, 0))

        # Button container with better spacing
        btn_container = Frame(control_frame, bootstyle="dark")
        btn_container.pack()

        self.start_btn = Button(btn_container, text="● Start", 
                               command=self.toggle_start, 
                               bootstyle="success", width=12)
        self.start_btn.grid(row=0, column=0, padx=5, pady=5)

        self.pause_btn = Button(btn_container, text="⏸ Pause", 
                               command=self.pause_monitoring, 
                               bootstyle="warning", width=12)
        self.pause_btn.grid(row=0, column=1, padx=5, pady=5)

        self.reset_btn = Button(btn_container, text="⟲ Reset", 
                               command=self.reset_data, 
                               bootstyle="secondary", width=12)
        self.reset_btn.grid(row=1, column=0, padx=5, pady=5)

        self.save_btn = Button(btn_container, text="💾 Save", 
                              command=self.save_data, 
                              bootstyle="info", width=12)
        self.save_btn.grid(row=1, column=1, padx=5, pady=5)

        # Settings button
        self.settings_btn = Button(btn_container, text="⚙ Settings", 
                                  command=self.open_settings, 
                                  bootstyle="dark-outline", width=25)
        self.settings_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=(10, 5))

    def toggle_start(self):
        """Toggle start/stop monitoring"""
        if not self.running:
            self.running = True
            self.start_btn.config(text="⏹ Stop", bootstyle="danger")
            self.status_label.config(text="Monitoring", bootstyle="success")
            self.progress.start(10)
        else:
            self.running = False
            self.start_btn.config(text="● Start", bootstyle="success")
            self.status_label.config(text="Stopped", bootstyle="secondary")
            self.progress.stop()

    def pause_monitoring(self):
        """Pause monitoring without stopping data collection"""
        self.paused = not self.paused
        
        if self.paused:
            self.pause_btn.config(text="▶ Resume", bootstyle="info")
            self.status_label.config(text="Paused", bootstyle="warning")
        else:
            self.pause_btn.config(text="⏸ Pause", bootstyle="warning")
            if self.running:
                self.status_label.config(text="Monitoring", bootstyle="success")

    def reset_data(self):
        """Reset all data and display"""
        self.x_data, self.y_data = [], []
        self.line.set_data([], [])
        if self.fill:
            self.fill.remove()
            self.fill = None
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
        self.temp_val.config(text="-- °C")
        self.status_label.config(text="Reset", bootstyle="secondary")

    def save_data(self):
        """Save data with timestamp"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"coagulex_data_{timestamp}.csv"
        
        with open(filename, "w") as f:
            f.write("Time,Temperature,Timestamp\n")
            for i, (x, y) in enumerate(zip(self.x_data, self.y_data)):
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", 
                                            time.localtime(time.time() - len(self.x_data) + i))
                f.write(f"{x},{y:.2f},{timestamp_str}\n")
        
        # Show save confirmation
        self.status_label.config(text=f"Saved: {filename}", bootstyle="info")
        self.root.after(3000, lambda: self.status_label.config(text="Ready", bootstyle="success"))

    def open_settings(self):
        """Open settings dialog (placeholder)"""
        self.status_label.config(text="Settings (Coming Soon)", bootstyle="info")
        self.root.after(2000, lambda: self.status_label.config(text="Ready", bootstyle="success"))

    def start_plot_update(self):
        """Update plot with modern animations and effects"""
        if (self.running and not self.paused and data_queue):
            
            temp = data_queue.pop(0)
            self.y_data.append(temp)
            self.x_data.append(len(self.x_data) * 0.1)  # Time in seconds
            
            # Keep only last 100 points for performance
            if len(self.x_data) > 100:
                self.x_data.pop(0)
                self.y_data.pop(0)
            
            # Update line
            self.line.set_data(self.x_data, self.y_data)
            
            # Add fill under the line for modern look
            if self.fill:
                self.fill.remove()
            if len(self.x_data) > 1:
                self.fill = self.ax.fill_between(self.x_data, self.y_data, 
                                               alpha=0.2, color=self.colors['accent_blue'])
            
            # Dynamic y-axis scaling
            if self.y_data:
                y_min, y_max = min(self.y_data), max(self.y_data)
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 1
                self.ax.set_ylim(y_min - margin, y_max + margin)
            
            # Update x-axis
            if self.x_data:
                self.ax.set_xlim(max(0, self.x_data[-1] - 10), self.x_data[-1] + 1)
            
            self.ax.relim()
            self.canvas.draw()
            
            # Update temperature display with color coding
            temp_color = "info"
            if temp > 35:
                temp_color = "warning"
            elif temp > 40:
                temp_color = "danger"
            elif temp < 30:
                temp_color = "secondary"
                
            self.temp_val.config(text=f"{temp:.1f} °C", bootstyle=temp_color)
        
        self.root.after(100, self.start_plot_update)


# Launch GUI
if __name__ == '__main__':
    threading.Thread(target=simulate_serial, daemon=True).start()
    root = tk.Tk()
    app = CoagulexApp(root)
    root.mainloop()
