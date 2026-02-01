from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB = "hospital.db"

# ------------------ DB HELPER ------------------
def query(sql, params=(), one=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.commit()
    con.close()
    return (rows[0] if rows else None) if one else rows

# ------------------ INIT DB ------------------
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Doctors table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialty TEXT
    )
    """)

    # Patients table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL
    )
    """)

    # Appointments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        time TEXT
    )
    """)

    # Prescriptions table
    cur.execute("DROP TABLE IF EXISTS prescriptions")
    cur.execute("""
    CREATE TABLE prescriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT,
        patient_name TEXT,
        age INTEGER,
        height REAL,
        weight REAL,
        medicines TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Users table (admin + doctors)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ------------------ DOCTORS LIST WITH EMAIL + PASSWORD ------------------
doctors = [
    {"name":"Dr. John Anderson","specialty":"Cardiology","email":"john@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Emma Wilson","specialty":"Neurology","email":"emma@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Michael Roberts","specialty":"Orthopedics","email":"michael@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Olivia Johnson","specialty":"Dermatology","email":"olivia@gmail.com","password":"svmhospital123"},
    {"name":"Dr. William Smith","specialty":"Pediatrics","email":"william@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Sophia Brown","specialty":"Gynecology","email":"sophia@gmail.com","password":"svmhospital123"},
    {"name":"Dr. James Davis","specialty":"Oncology","email":"james@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Isabella Martinez","specialty":"Psychiatry","email":"isabella@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Benjamin Lee","specialty":"Radiology","email":"benjamin@gmail.com","password":"svmhospital123"},
    {"name":"Dr. Mia Taylor","specialty":"Gastroenterology","email":"mia@gmail.com","password":"svmhospital123"}
]

# ------------------ SEED DOCTORS + USERS ------------------
def seed_doctors_and_users():
    if query("SELECT * FROM doctors"):
        return

    # Seed doctors and doctor users
    for d in doctors:
        query("INSERT INTO doctors (name, specialty) VALUES (?,?)", (d["name"], d["specialty"]))
        query("INSERT INTO users (role, username, password) VALUES (?,?,?)", ("doctor", d["email"], d["password"]))

    # Seed admin user
    query("INSERT INTO users (role, username, password) VALUES (?,?,?)", ("admin", "svanam", "admin@2110"))

seed_doctors_and_users()

# ------------------ PATIENT ROUTES ------------------
@app.route("/patients", methods=["POST"])
def add_patient():
    data = request.get_json()
    if query("SELECT * FROM patients WHERE email=?", (data["email"],), one=True):
        return jsonify({"error": "Email exists"}), 409

    query("""
    INSERT INTO patients (name,email,age,gender,height,weight)
    VALUES (?,?,?,?,?,?)
    """, (
        data["name"], data["email"], data["age"],
        data["gender"], data["height"], data["weight"]
    ))
    return jsonify({"status": "patient added"})

@app.route("/patients", methods=["GET"])
def get_patients():
    rows = query("SELECT * FROM patients")
    return jsonify([dict(r) for r in rows])

# ------------------ APPOINTMENT ROUTES ------------------
@app.route("/appointments", methods=["POST"])
def book_appointment():
    data = request.get_json()
    query("""
    INSERT INTO appointments (patient_id, doctor_id, date, time)
    VALUES (?,?,?,?)
    """, (
        data["patient_id"], data["doctor_id"],
        data["date"], data["time"]
    ))
    return jsonify({"status": "booked"})

@app.route("/appointments", methods=["GET"])
def get_appointments():
    email = request.args.get("email")
    doctor = request.args.get("doctor")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    if email:
        cur.execute("""
        SELECT a.id, d.name AS doctor, a.date, a.time
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE p.email = ?
        ORDER BY a.date DESC, a.time DESC
        """, (email,))

    elif doctor:
        cur.execute("""
        SELECT a.id, p.id AS patient_id, p.name AS patient, p.age, p.gender, p.height, p.weight,
               a.date, a.time
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE d.name = ?
        ORDER BY a.date DESC, a.time DESC
        """, (doctor,))

    else:
        # Admin - all appointments
        cur.execute("""
        SELECT 
            a.id,
            p.name AS patient,
            d.name AS doctor,
            a.date,
            a.time
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.date DESC, a.time DESC
        """)

    rows = cur.fetchall()
    con.close()

    return jsonify([dict(r) for r in rows])

# ------------------ PRESCRIPTION ROUTES ------------------
@app.route("/prescriptions", methods=["GET","POST"])
def prescriptions():
    if request.method=="POST":
        data=request.get_json()
        query("""
        INSERT INTO prescriptions
        (doctor_name, patient_name, age, height, weight, medicines)
        VALUES (?,?,?,?,?,?)
        """,(
            data["doctorName"],
            data["patientName"],
            data.get("age"),
            data.get("height"),
            data.get("weight"),
            data["medicines"]
        ))
        return jsonify({"status":"saved"}), 201

    rows = query("SELECT * FROM prescriptions ORDER BY created_at DESC")
    return jsonify([dict(r) for r in rows])

# ------------------ LOGIN ROUTE ------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = query("""
    SELECT * FROM users
    WHERE username=? AND password=?
    """, (data["username"], data["password"]), one=True)

    if not user:
        return jsonify({"error":"Invalid login"}), 401

    return jsonify({
        "status":"success",
        "role": user["role"],
        "username": user["username"]
    })

# ------------------ RUN APP ------------------
if __name__=="__main__":
    app.run(debug=True, port=8000)
