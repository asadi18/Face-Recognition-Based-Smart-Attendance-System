# Face Recognition Based Smart Attendance System

A Python Flask web application for student attendance using face recognition.

## University

Southern University Bangladesh

## Features

- Student registration
- Register student with name, roll number, department, batch, and face image
- Webcam-based face capture
- Face recognition attendance
- Attendance saved in Excel
- Duplicate attendance prevention for the same day
- Attendance records page
- Excel download option

## Technologies Used

- Python
- Flask
- OpenCV / face_recognition
- dlib
- NumPy
- Pandas
- OpenPyXL
- HTML
- CSS

## Project Structure

```text
smart-face-attendance-system/
│
├── app.py
├── requirements.txt
├── students.xlsx
├── attendance.xlsx
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── uploads/
│
└── templates/
    ├── base.html
    ├── index.html
    ├── register.html
    ├── attendance.html
    └── records.html
