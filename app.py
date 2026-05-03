import os
import base64
from datetime import datetime

import pandas as pd
from deepface import DeepFace
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "smart_attendance_secret_key"

UPLOAD_FOLDER = "static/uploads"
STUDENTS_FILE = "students.xlsx"
ATTENDANCE_FILE = "attendance.xlsx"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def setup_excel_files():
    try:
        pd.read_excel(STUDENTS_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=["Name", "Roll", "Department", "Batch", "Image"])
        df.to_excel(STUDENTS_FILE, index=False, engine="openpyxl")

    try:
        pd.read_excel(ATTENDANCE_FILE, engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=["Name", "Roll", "Date", "Time", "Status"])
        df.to_excel(ATTENDANCE_FILE, index=False, engine="openpyxl")


def save_base64_image(base64_data, filename):
    image_data = base64_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    image_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(image_path, "wb") as f:
        f.write(image_bytes)

    return image_path


def validate_face(image_path):
    try:
        DeepFace.extract_faces(
            img_path=image_path,
            detector_backend="opencv",
            enforce_detection=True
        )
        return True
    except Exception as e:
        print("Face validation error:", e)
        return False


def find_matching_student(captured_image_path):
    students = pd.read_excel(STUDENTS_FILE, engine="openpyxl")

    if students.empty:
        return None

    for _, row in students.iterrows():
        registered_image_path = row["Image"]

        if not os.path.exists(registered_image_path):
            continue

        try:
            result = DeepFace.verify(
                img1_path=captured_image_path,
                img2_path=registered_image_path,
                model_name="Facenet",
                detector_backend="opencv",
                enforce_detection=False
            )

            if result.get("verified"):
                return {
                    "Name": row["Name"],
                    "Roll": str(row["Roll"])
                }

        except Exception as e:
            print("Matching error:", e)

    return None


@app.route("/")
def index():
    setup_excel_files()

    students = pd.read_excel(STUDENTS_FILE, engine="openpyxl")
    attendance_df = pd.read_excel(ATTENDANCE_FILE, engine="openpyxl")

    today = datetime.now().strftime("%Y-%m-%d")
    today_attendance = attendance_df[attendance_df["Date"].astype(str) == today]

    return render_template(
        "index.html",
        total_students=len(students),
        today_attendance=len(today_attendance)
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    setup_excel_files()

    if request.method == "POST":
        name = request.form.get("name")
        roll = request.form.get("roll")
        department = request.form.get("department")
        batch = request.form.get("batch")
        captured_image = request.form.get("captured_image")
        uploaded_image = request.files.get("image")

        if not name or not roll:
            flash("Name and Roll No are required.", "danger")
            return redirect(url_for("register"))

        if not captured_image and (not uploaded_image or uploaded_image.filename == ""):
            flash("Please capture or upload a face image.", "danger")
            return redirect(url_for("register"))

        students = pd.read_excel(STUDENTS_FILE, engine="openpyxl")

        if str(roll) in students["Roll"].astype(str).values:
            flash("This Roll No is already registered.", "danger")
            return redirect(url_for("register"))

        filename = f"{roll}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

        if captured_image:
            image_path = save_base64_image(captured_image, filename)
        else:
            safe_name = secure_filename(uploaded_image.filename)
            filename = f"{roll}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            uploaded_image.save(image_path)

        face_valid = validate_face(image_path)

        if not face_valid:
            if os.path.exists(image_path):
                os.remove(image_path)

            flash("No face found. Please use a clear front-facing image.", "danger")
            return redirect(url_for("register"))

        new_student = pd.DataFrame([{
            "Name": name,
            "Roll": roll,
            "Department": department,
            "Batch": batch,
            "Image": image_path
        }])

        students = pd.concat([students, new_student], ignore_index=True)
        students.to_excel(STUDENTS_FILE, index=False, engine="openpyxl")

        flash("Student registered successfully.", "success")
        return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    setup_excel_files()

    if request.method == "POST":
        captured_image = request.form.get("captured_image")

        if not captured_image:
            flash("Please capture image from webcam.", "danger")
            return redirect(url_for("attendance"))

        filename = f"attendance_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        image_path = save_base64_image(captured_image, filename)

        face_valid = validate_face(image_path)

        if not face_valid:
            flash("No face found. Please stand clearly in front of webcam.", "danger")
            return redirect(url_for("attendance"))

        student = find_matching_student(image_path)

        if not student:
            flash("Face not recognized. Student not registered.", "danger")
            return redirect(url_for("attendance"))

        name = student["Name"]
        roll = student["Roll"]

        attendance_df = pd.read_excel(ATTENDANCE_FILE, engine="openpyxl")

        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        already_marked = attendance_df[
            (attendance_df["Roll"].astype(str) == str(roll)) &
            (attendance_df["Date"].astype(str) == today)
        ]

        if not already_marked.empty:
            flash(f"Attendance already marked today for {name} - Roll {roll}.", "warning")
            return redirect(url_for("attendance"))

        new_attendance = pd.DataFrame([{
            "Name": name,
            "Roll": roll,
            "Date": today,
            "Time": current_time,
            "Status": "Present"
        }])

        attendance_df = pd.concat([attendance_df, new_attendance], ignore_index=True)
        attendance_df.to_excel(ATTENDANCE_FILE, index=False, engine="openpyxl")

        flash(f"Attendance marked successfully for {name} - Roll {roll}.", "success")
        return redirect(url_for("attendance"))

    return render_template("attendance.html")


@app.route("/records")
def records():
    setup_excel_files()

    attendance_df = pd.read_excel(ATTENDANCE_FILE, engine="openpyxl")
    records = attendance_df.to_dict(orient="records")

    return render_template("records.html", records=records)


@app.route("/download-attendance")
def download_attendance():
    return send_file(ATTENDANCE_FILE, as_attachment=True)


if __name__ == "__main__":
    setup_excel_files()
    app.run(host="0.0.0.0", port=5000, debug=True)