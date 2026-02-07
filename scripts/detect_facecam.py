import cv2
import numpy as np
import sys
import os

def detect_face_and_cam(frame_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    img = cv2.imread(frame_path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    results = []
    for (x, y, w, h) in faces:
        results.append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
             res = detect_face_and_cam(path)
             if res:
                 print(f"FRAME {path}: {res}")
    else:
        frames_dir = '/mnt/d/ai-videos/debug_frames/'
        for frame_file in sorted(os.listdir(frames_dir)):
            if frame_file.endswith('.jpg'):
                res = detect_face_and_cam(os.path.join(frames_dir, frame_file))
                if res:
                    print(f"FRAME {frame_file}: {res}")