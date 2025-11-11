import numpy as np
import cv2 as cv

# Open both webcams
cap0 = cv.VideoCapture(0)
cap1 = cv.VideoCapture(1)

# Check if both webcams opened successfully
if not cap0.isOpened():
    print("Error: Could not open webcam 0.")
    exit()
if not cap1.isOpened():
    print("Error: Could not open webcam 1.")
    exit()

# Initialize previous centers and distances for each camera
prev_centers = [None, None]
total_distances = [0, 0]

def process_frame(cap, cam_id):
    global prev_centers, total_distances

    ret, frame = cap.read()
    if not ret:
        return None, None, None

    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blurred, 100, 200)
    contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    if contours:
        largest = max(contours, key=cv.contourArea)
        x, y, w, h = cv.boundingRect(largest)
        center = (x + w // 2, y + h // 2)

        cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv.circle(frame, center, 5, (0, 0, 255), -1)

        if prev_centers[cam_id]:
            dx = center[0] - prev_centers[cam_id][0]
            dy = center[1] - prev_centers[cam_id][1]
            dist = np.sqrt(dx**2 + dy**2)
            total_distances[cam_id] += dist

            cv.putText(frame, f"Moved: {dist:.2f}px", (10, 30),
                       cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv.putText(frame, f"Total: {total_distances[cam_id]:.2f}px", (10, 60),
                       cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        prev_centers[cam_id] = center

    return frame, edges, contours

while True:
    frame0, edges0, _ = process_frame(cap0, 0)
    frame1, edges1, _ = process_frame(cap1, 1)

    if frame0 is not None:
        cv.imshow('Camera 0 - Tracking', frame0)
        cv.imshow('Camera 0 - Edges', edges0)

    if frame1 is not None:
        cv.imshow('Camera 1 - Tracking', frame1)
        cv.imshow('Camera 1 - Edges', edges1)

    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap0.release()
cap1.release()
cv.destroyAllWindows()
