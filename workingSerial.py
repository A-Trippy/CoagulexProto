import serial
import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import cv2


# Configure serial port
ser = serial.Serial('COM4', 9600, timeout=1)  # Replace COM3 with your Arduino port

# Buffers to hold recent values
buffer_size = 100  # Number of points to display
t1_data = deque([0]*buffer_size, maxlen=buffer_size)
t2_data = deque([0]*buffer_size, maxlen=buffer_size)
x_data = deque(range(buffer_size), maxlen=buffer_size)

# Create figure and axes
fig, ax = plt.subplots()
line1, = ax.plot([], [], label='T1', color='red')
line2, = ax.plot([], [], label='T2', color='blue')
ax.set_ylim(0, 100)  # Adjust based on expected value range
ax.set_xlim(0, buffer_size)
ax.set_title("Live T1 & T2 Data from Arduino")
ax.set_xlabel("Sample #")
ax.set_ylabel("Temperature (°C)")
ax.legend(loc='upper right')

# Update function for animation
def update(frame):
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    match = re.search(r'T1:(\d+\.\d+)\s+T2:(\d+\.\d+)', line)
    if match:
        t1 = float(match.group(1))
        t2 = float(match.group(2))
        t1_data.append(t1)
        t2_data.append(t2)

    line1.set_ydata(t1_data)
    line2.set_ydata(t2_data)
    line1.set_xdata(x_data)
    line2.set_xdata(x_data)
    return line1, line2

def list_cameras(max_index=10):
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"Camera index {index} is available.")
            cap.release()
        else:
            print(f"Camera index {index} is not available.")


# Set up the animation
ani = animation.FuncAnimation(fig, update, interval=100, blit=True)

# Show plot
plt.tight_layout()
plt.show()
list_cameras()


# Cleanup on close
ser.close()



