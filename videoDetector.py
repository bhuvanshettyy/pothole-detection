import cv2 as cv
import os
from imageDetector import send_telegram_message  # Import send_telegram_message from imageDetector
import logging
from geopy.geocoders import Nominatim
from tkinter import simpledialog
from tkinter.messagebox import showinfo  # Correct import for showinfo

def detectPotholeonVideo(filename, save_location_data):
    try:
        class_name = []
        with open(os.path.join("project_files", 'obj.names'), 'r') as f:
            class_name = [cname.strip() for cname in f.readlines()]

        # Load the YOLOv4-tiny model
        net1 = cv.dnn.readNet('project_files/yolov4_tiny.weights', 'project_files/yolov4_tiny.cfg')
        model1 = cv.dnn_DetectionModel(net1)
        model1.setInputParams(size=(640, 480), scale=1 / 255, swapRB=True)

        cap = cv.VideoCapture(filename)
        if not cap.isOpened():
            logging.error("Error: Could not open video file!")
            return 0  # Return 0 to indicate failure
        else:
            logging.info("Video successfully opened.")

        frame_counter = 0
        max_potholes_in_frame = 0  # Track maximum potholes in any frame

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Object detection
            classes, scores, boxes = model1.detect(frame, 0.5, 0.4)
            current_frame_potholes = len(classes)
            
            # Update maximum potholes if current frame has more
            max_potholes_in_frame = max(max_potholes_in_frame, current_frame_potholes)

            for (classid, score, box) in zip(classes, scores, boxes):
                print(f"Detected class ID: {classid}, Score: {score}")  # Debugging output
                if classid == 0:  # Assuming 'pothole' is class ID 0
                    cv.rectangle(frame, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 1)
                cv.putText(frame, f"{class_name[classid]}: {round(float(score) * 100, 2)}%", 
                           (box[0], box[1] - 10), cv.FONT_HERSHEY_COMPLEX, 0.5, (255, 0, 0), 1)

            # Display current count on frame
            cv.putText(frame, f"Potholes in frame: {current_frame_potholes}", 
                      (10, 30), cv.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

            # Display the frame
            cv.imshow('Video', frame)

            # Check for 'q' key press to exit the loop
            if cv.waitKey(1) & 0xFF == ord('q'):
                break

            frame_counter += 1

        cap.release()
        cv.destroyAllWindows()

        # Send the pothole count to Telegram after processing the video
        message = f"Pothole Detection Report:\nTotal Detected Potholes in Video: {max_potholes_in_frame}"
        send_telegram_message(message)

        # After detecting potholes, return the count
        return max_potholes_in_frame  # Return the maximum potholes detected
    except Exception as e:
        logging.error(f"An error occurred during video processing: {e}")
        return 0  # Return 0 to indicate failure
