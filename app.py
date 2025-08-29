from flask import Flask, render_template, request, session, url_for, redirect
from flask_restful import Api
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecret"
api = Api(app)

#NO CACHE
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Mapping letter grades to numeric points
grade_points = {
    "A+": 10,
    "A": 9,
    "B+": 8,
    "B": 7,
    "C+": 6,
    "C": 5,
    "D": 4,
    "F": 0
}

#DB CONNECTION
def get_db_connection():
    conn = sqlite3.connect("student_data_sqlite.db")
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn

#HOME / LOGIN
@app.route("/")
def home():
    return render_template('index.html', error=None)

@app.route('/dashboard', methods=['POST'])
def handle_post():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Teachers WHERE TeacherID = ? AND Password = ?",
        (username, password)
    )
    teacher = cursor.fetchone()
    cursor.close()
    conn.close()

    if teacher:
        session['TeacherID'] = teacher['TeacherID']
        session['Name'] = teacher['Name']
        session['Email'] = teacher['Email']
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html', error="Invalid Credentials")

@app.route('/dashboard')
def dashboard():
    if 'TeacherID' not in session:
        return redirect(url_for('home'))
    teacher = {
        "TeacherID": session["TeacherID"],
        "Name": session["Name"],
        "Email": session["Email"]
    }
    return render_template('dashboard.html', teacher=teacher)

#LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

#ADD STUDENTS
@app.route("/add_students")
def add_students_page():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    teacherid = session["TeacherID"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(RollNo) FROM Students WHERE TeacherID = ?", (teacherid,))
    last_roll = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    next_roll = 1 if last_roll is None else last_roll + 1
    return render_template("add_students.html", teacherid=teacherid, nextroll=next_roll, error=None)

@app.route("/add_student", methods=["POST"])
def add_student():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    name = request.form["name"]
    teacherid = session["TeacherID"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(RollNo) FROM Students WHERE TeacherID = ?", (teacherid,))
    last_roll = cursor.fetchone()[0]
    next_roll = 1 if last_roll is None else last_roll + 1

    cursor.execute(
        "INSERT INTO Students (RollNo, Name, TeacherID) VALUES (?, ?, ?)",
        (next_roll, name, teacherid)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

#EDIT STUDENTS
@app.route("/edit_students")
def edit_students_page():
    if "TeacherID" not in session:
        return redirect(url_for("home"))
    return render_template("edit_students.html", teacherid=session["TeacherID"], error=None)

@app.route("/dashboard/edit_student", methods=["POST"])
def edit_student():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    teacherid = session["TeacherID"]
    rollno = request.form["rollno"]
    new_name = request.form["name"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Students SET Name = ? WHERE RollNo = ? AND TeacherID = ?",
        (new_name, rollno, teacherid)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

#DELETE STUDENTS
@app.route("/dashboard/delete_students")
def delete_students_page():
    if "TeacherID" not in session:
        return redirect(url_for("home"))
    return render_template("delete_students.html", teacherid=session["TeacherID"], error=None)

@app.route("/delete_student", methods=["POST"])
def delete_student():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    teacherid = session["TeacherID"]
    rollno = request.form["rollno"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM Students WHERE RollNo = ? AND TeacherID = ?",
        (rollno, teacherid)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

#SUMMARIZE
@app.route("/dashboard/summarize")
def summarize_page():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    teacherid = session["TeacherID"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT StudentID, Name FROM Students WHERE TeacherID = ?", (teacherid,))
    students = cursor.fetchall()
    cursor.execute("SELECT SubjectID, SubjectName FROM Subjects")
    subjects = cursor.fetchall()
    subject_map = {sub["SubjectID"]: sub["SubjectName"] for sub in subjects}

    cursor.execute("""
        SELECT g.StudentID, g.SubjectID, g.Grade
        FROM Grades g
        JOIN Students s ON g.StudentID = s.StudentID
        WHERE s.TeacherID = ?
    """, (teacherid,))
    grades = cursor.fetchall()

    student_table = {s["StudentID"]: {"Name": s["Name"], "Grades": {}} for s in students}
    for g in grades:
        sid = g["StudentID"]
        subject_name = subject_map[g["SubjectID"]]
        student_table[sid]["Grades"][subject_name] = g["Grade"]

    topper = None
    max_total = -1
    for s in student_table.values():
        total = sum(grade_points.get(g, 0) for g in s["Grades"].values())
        if total > max_total:
            max_total = total
            topper = s["Name"]

    toppers_per_subject = {}
    for sub in subject_map.values():
        max_point = -1
        top_student = None
        for s in student_table.values():
            if sub in s["Grades"]:
                points = grade_points.get(s["Grades"][sub], 0)
                if points > max_point:
                    max_point = points
                    top_student = s["Name"]
        toppers_per_subject[sub] = {
            "Name": top_student,
            "Grade": [k for k,v in grade_points.items() if v==max_point][0] if max_point >=0 else None
        }

    cursor.close()
    conn.close()

    return render_template(
        "summarize.html",
        student_table=student_table,
        subjects=list(subject_map.values()),
        overall_topper=topper,
        toppers_per_subject=toppers_per_subject
    )

#MARKS ALLOTMENT
@app.route("/marks_allotment")
def marks_allotment_page():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    subjects = get_subjects()
    return render_template("marks_allotment.html", subjects=subjects, error=None)

@app.route("/marks_allotment", methods=["POST"])
def add_marks():
    if "TeacherID" not in session:
        return redirect(url_for("home"))

    rollno = request.form["rollno"]
    grades = {}
    for key, val in request.form.items():
        if key.startswith("subject_"):
            if val not in grade_points:
                return render_template("marks_allotment.html", subjects=get_subjects(), error=f"Invalid grade: {val}")
            grades[int(key.split("_")[1])] = val

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT StudentID FROM Students WHERE RollNo=? AND TeacherID=?", (rollno, session["TeacherID"]))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        conn.close()
        return render_template("marks_allotment.html", subjects=get_subjects(), error="Student not found")

    student_id = student[0]

    for subject_id, grade in grades.items():
        cursor.execute("""
            INSERT OR REPLACE INTO Grades (StudentID, SubjectID, Grade)
            VALUES (?, ?, ?)
        """, (student_id, subject_id, grade))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))

def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SubjectID, SubjectName FROM Subjects")
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()
    return subjects

#RUN
if __name__ == "__main__":
    app.run(debug=True)
