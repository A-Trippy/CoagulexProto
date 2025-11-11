import numpy as np
import cv2 as cv

vidCap = cv.VideoCapture(0)

if not vidCap.isOpened():
    print("Error: Could not open video.")
    exit()

prev_center = None
total_distance = 0
tracked_contour = None  # Lock-on reference
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

while True:
    ret, frame = vidCap.read()
    if not ret:
        break

    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blurred, 100, 200)
    contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    current_contour = None

    if contours:
        if tracked_contour is None:
            # First detection: lock on to largest
            tracked_contour = max(contours, key=cv.contourArea)
            current_contour = tracked_contour
        else:
            # Look for a similar contour in current frame
            for contour in contours:
                if contours_similar(tracked_contour, contour):
                    current_contour = contour
                    tracked_contour = contour  # Update lock
                    break

    if current_contour is not None:
        center = get_center(current_contour)
        cv.drawContours(frame, [current_contour], -1, (0, 255, 0), 2)
        cv.circle(frame, center, 5, (0, 0, 255), -1)

        if prev_center is not None:
            dy = center[1] - prev_center[1]
            total_distance += dy

        prev_center = center
        missing_frames = 0  # Reset
    else:
        missing_frames += 1
        if missing_frames > max_missing_frames:
            tracked_contour = None  # Lost track, allow relock
            prev_center = None

    cv.putText(frame, f"Total: {total_distance:.2f}px", (10, 60),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv.imshow("Contour Tracking", frame)

    if cv.waitKey(1) & 0xFF == ord('q'):
        break

vidCap.release()
cv.destroyAllWindows()

conv_factor = 0.264  # Example: pixel to cm
print(f"Total distance moved: {total_distance * conv_factor:.2f} cm")