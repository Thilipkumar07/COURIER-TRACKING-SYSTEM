!pip install gradio

import os
import sqlite3
import random
import string
from datetime import datetime
import gradio as gr

DB = "courier_system.db"
TN_CITIES = [
    "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli",
    "Salem", "Erode", "Tirunelveli", "Vellore",
    "Thoothukudi", "Dindigul"
]

# Setup DB (reset every time you run)
if os.path.exists(DB):
    os.remove(DB)

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("""
CREATE TABLE courier(
    tracking_id TEXT PRIMARY KEY,
    user_name TEXT,
    from_loc TEXT,
    to_loc TEXT,
    weight_kg REAL,
    price_inr REAL,
    speed TEXT,
    booked_on TEXT,
    current_loc TEXT,
    exp_days INTEGER
)
""")
c.execute("""
CREATE TABLE admin(
    username TEXT PRIMARY KEY,
    password TEXT
)
""")
c.execute("INSERT INTO admin VALUES ('admin', 'admin123')")
conn.commit()
conn.close()

def gen_tid():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    while True:
        tid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        cur.execute("SELECT 1 FROM courier WHERE tracking_id=?", (tid,))
        if not cur.fetchone():
            conn.close()
            return tid

def get_all_ids():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT tracking_id FROM courier ORDER BY booked_on DESC")
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    return ids

def book_courier(name, frm, to, weight, speed):
    if not name.strip() or frm not in TN_CITIES or to not in TN_CITIES or weight <= 0:
        return "❌ Fill all fields correctly.", ""
    if frm == to:
        return "❌ 'From' and 'To' locations must be different.", ""
    base_price = weight * 15
    exp_days = 5
    if speed == "Fast Delivery":
        base_price *= 1.5
        exp_days = 2
    tid = gen_tid()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courier(tracking_id, user_name, from_loc, to_loc, weight_kg, price_inr, speed, booked_on, current_loc, exp_days)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tid, name, frm, to, weight, base_price, speed, now, frm, exp_days))
    conn.commit()
    conn.close()
    return (
        f"✅ Booked! Tracking ID: {tid}\nPrice: ₹{base_price:.2f}\nEstimated delivery: {exp_days} days",
        tid
    )

def track_courier(tid):
    tid = tid.strip()
    if not tid:
        return "❌ Please enter Tracking ID."
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT user_name, from_loc, to_loc, current_loc, exp_days
        FROM courier WHERE tracking_id=?
    """, (tid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "❌ Tracking ID not found."
    user, frm, to, cur_loc, days = row
    return (f"Tracking ID: {tid}\nUser: {user}\nFrom: {frm}\nTo: {to}\nCurrent location: {cur_loc}\nEstimated days left: {days}")

def admin_login(username, password):
    username = username.strip()
    password = password.strip()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admin WHERE username=? AND password=?", (username, password))
    result = cur.fetchone()
    conn.close()
    if result:
        all_ids = get_all_ids()
        return (
            "✅ Login successful.",
            gr.update(choices=all_ids),  # Update the dropdown with choices
            gr.update(visible=True)      # Show the admin panel
        )
    else:
        return (
            "❌ Invalid username or password.",
            gr.update(choices=[]),
            gr.update(visible=False)
        )

def admin_update(tracking_id, new_location, new_days):
    if not tracking_id:
        return "❌ Select a Tracking ID."
    if new_location not in TN_CITIES:
        return "❌ Invalid location."
    if new_days < 1:
        return "❌ Expected days must be >= 1."
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE courier SET current_loc=?, exp_days=? WHERE tracking_id=?", (new_location, int(new_days), tracking_id))
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated:
        return "✅ Update successful."
    else:
        return "❌ Tracking ID not found."

def admin_view_all():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT tracking_id, user_name, from_loc, to_loc, current_loc, exp_days
        FROM courier ORDER BY booked_on DESC
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No bookings found."
    header = "Tracking ID | User | From → To | Current Location | ETA (days)"
    lines = [header, "-" * len(header)]
    for tid, user, frm, to, cur_loc, days in rows:
        lines.append(f"{tid} | {user} | {frm} → {to} | {cur_loc} | {days}")
    return "\n".join(lines)

# Gradio UI
with gr.Blocks() as app:
    gr.Markdown("# 📦 Courier Tracking System")

    with gr.Tab("Book Courier"):
        name = gr.Textbox(label="Your Name")
        frm = gr.Dropdown(choices=TN_CITIES, label="From (Tamil Nadu only)")
        to = gr.Dropdown(choices=TN_CITIES, label="To (Tamil Nadu only)")
        weight = gr.Number(label="Weight (kg)", value=1, minimum=0.1)
        speed = gr.Radio(["Normal Delivery", "Fast Delivery"], label="Delivery Speed", value="Normal Delivery")
        btn_book = gr.Button("Book Courier")
        out_book = gr.Textbox(label="Booking Status", interactive=False, lines=3)
        tid_out = gr.Textbox(label="Tracking ID", interactive=False)

        btn_book.click(book_courier, inputs=[name, frm, to, weight, speed], outputs=[out_book, tid_out])

    with gr.Tab("Track Courier"):
        tid_in = gr.Textbox(label="Enter Tracking ID")
        btn_track = gr.Button("Track Courier")
        out_track = gr.Textbox(label="Tracking Information", interactive=False, lines=6)

        btn_track.click(track_courier, inputs=tid_in, outputs=out_track)

    with gr.Tab("Admin"):
        admin_user = gr.Textbox(label="Username")
        admin_pass = gr.Textbox(label="Password", type="password")
        btn_login = gr.Button("Login")
        login_status = gr.Textbox(label="Login Status", interactive=False)

        with gr.Column(visible=False) as admin_panel:
            select_tid = gr.Dropdown(label="Select Tracking ID", choices=[])
            new_loc = gr.Dropdown(choices=TN_CITIES, label="Update Current Location")
            new_days = gr.Number(label="Update Expected Days", value=5, minimum=1, precision=0)
            btn_update = gr.Button("Update")
            update_status = gr.Textbox(label="Update Status", interactive=False)
            btn_view_all = gr.Button("View All Bookings")
            view_all_out = gr.Textbox(label="All Courier Bookings", interactive=False, lines=10)

        btn_login.click(
            admin_login,
            inputs=[admin_user, admin_pass],
            outputs=[login_status, select_tid, admin_panel]
        )
        btn_update.click(
            admin_update,
            inputs=[select_tid, new_loc, new_days],
            outputs=update_status
        )
        btn_view_all.click(
            admin_view_all,
            inputs=None,
            outputs=view_all_out
        )

app.launch()
