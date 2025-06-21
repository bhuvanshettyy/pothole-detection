import cv2
import os
import requests

# Telegram Bot Token and Chat ID
BOT_TOKEN = "7781878675:AAHzuvrHqrWAhZ3bneaP4USS5uog68KfJ5U"
CHAT_ID = "5018333444"

def send_telegram_message(message):
    """Function to send a message to the Telegram bot."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

def detectPotholeonImage(filename):
    """Function to detect potholes in an image and send a message to Telegram."""
    img = cv2.imread(filename)
    
    if img is None:
        print("Error: Image not loaded!")
        return 0  # Return 0 to indicate no potholes detected or image loading failure
    else:
        print("Image successfully loaded.")

    # Load YOLO object detection model
    with open(os.path.join("project_files", 'obj.names'), 'r') as f:
        classes = f.read().splitlines()

    net = cv2.dnn.readNet('project_files/yolov4_tiny.weights', 'project_files/yolov4_tiny.cfg')
    model = cv2.dnn_DetectionModel(net)
    model.setInputParams(scale=1 / 255, size=(416, 416), swapRB=True)

    classIds, scores, boxes = model.detect(img, confThreshold=0.6, nmsThreshold=0.4)
    print(f"Detections: {len(classIds)}")  # Debugging output

    # Draw boxes and labels on detected potholes
    potholes_count = 0  # Variable to track potholes
    for (classId, score, box) in zip(classIds, scores, boxes):
        print(f"Detected class ID: {classId}, Score: {score}")  # Debugging output
        if classId == 0:  # Assuming 'pothole' is class ID 0
            potholes_count += 1
            cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)
            cv2.putText(img, f"Pothole ({score:.2f})", (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Display the image with detections
    cv2.imshow("Pothole Identification", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print("Image displayed successfully.")

    # Send the pothole count message to Telegram
    message = f"Pothole Detection Report:\nTotal Detected Potholes in Image: {potholes_count}"
    send_telegram_message(message)

    return potholes_count  # Return the potholes count
