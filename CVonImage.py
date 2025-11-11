import numpy as np
import cv2 as cv

# Load a single image
image_path = "UT Coagulex Image.jpg"
frame = cv.imread(image_path)

if frame is None:
    print("Error: Could not load image.")
    exit()

def get_center(contour):
    x, y, w, h = cv.boundingRect(contour)
    return (x + w // 2, y + h // 2)

# Preprocessing
gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
blurred = cv.GaussianBlur(gray, (5, 5), 0)
edges = cv.Canny(blurred, 100, 200)
contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

# Find and draw the largest contour
if contours:
    largest_contour = max(contours, key=cv.contourArea)
    center = get_center(largest_contour)
    
    cv.drawContours(frame, [largest_contour], -1, (0, 255, 0), 2)
    cv.circle(frame, center, 5, (0, 0, 255), -1)
    cv.putText(frame, f"Center: {center}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
else:
    print("No contours found.")

# Display result
cv.imshow("Image Contour", frame)
cv.waitKey(0)
cv.destroyAllWindows()
