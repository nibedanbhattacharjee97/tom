import streamlit as st
from datetime import datetime
import sqlite3
import io
from streamlit_option_menu import option_menu
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'signed_up' not in st.session_state:
    st.session_state.signed_up = False

def get_db_connection(db_name):
    try:
        conn = sqlite3.connect(db_name)
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {e}")
        return None

def create_user_table():
    conn = get_db_connection('users.db')
    if conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                email TEXT UNIQUE
            )
        ''')
        conn.commit()
        conn.close()

def sign_up():
    conn = get_db_connection('users.db')
    if conn:
        c = conn.cursor()
        with st.form("sign_up_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            email = st.text_input("Email")

            if password != confirm_password:
                st.error("Passwords do not match")
                return

            submit = st.form_submit_button("Sign Up")

            if submit:
                # Hash the password before saving
                hashed_password = generate_password_hash(password)

                # Check if the username is already taken
                c.execute("SELECT * FROM users WHERE username=?", (username,))
                existing_user = c.fetchone()

                if existing_user:
                    st.warning("Username already taken. Please choose a different one.")
                else:
                    c.execute('''
                        INSERT INTO users (username, password, email)
                        VALUES (?, ?, ?)
                    ''', (username, hashed_password, email))
                    conn.commit()
                    st.session_state.signed_up = True
                    st.success("User successfully signed up. You can now log in.")
        conn.close()

def login():
    conn = get_db_connection('users.db')
    if conn:
        c = conn.cursor()
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                c.execute("SELECT * FROM users WHERE username=?", (username,))
                user = c.fetchone()

                if user:
                    hashed_password = user[2]
                    if check_password_hash(hashed_password, password):
                        st.session_state.logged_in = True
                        st.success(f"Logged in as {username}")
                    else:
                        st.error("Incorrect password. Please try again.")
                else:
                    st.error("Username not found. Please sign up if you don't have an account.")
        conn.close()

# Function to upload technician details
def upload_technician():
    conn = get_db_connection('actual.db')
    if conn:
        c = conn.cursor()
        with st.form("upload_technician_form"):
            name = st.text_input("Technician Name")
            phone = st.text_input("Phone Number")
            address = st.text_input("Address")
            photo = st.file_uploader("Upload Photo", type=["jpeg", "jpg", "png"])
            tech_certificate = st.file_uploader("Upload Technical Certificate", type=["pdf"])
            submit = st.form_submit_button("Upload Technician Details")

            if submit:
                if name and phone and address and photo and tech_certificate:
                    uploaded_at = datetime.now().isoformat()

                    # Generate TechId
                    c.execute("SELECT MAX(id) FROM technicians")
                    max_id = c.fetchone()[0]
                    if max_id is None:
                        max_id = 0
                    tech_id = f"TECH-{max_id + 1:03}"

                    # Convert files to binary
                    photo_data = photo.read()
                    tech_certificate_data = tech_certificate.read()

                    # Insert into database
                    c.execute('''
                        INSERT INTO technicians (TechId, name, phone, address, photo, tech_certificate, uploaded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (tech_id, name, phone, address, photo_data, tech_certificate_data, uploaded_at))
                    conn.commit()
                    st.success(f"Details uploaded for {name}. Technician ID: {tech_id}")
                else:
                    st.error("Please fill all the fields and upload the required files")
        conn.close()

# Function to book technician
def book_technician():
    conn = get_db_connection('actual.db')
    if conn:
        c = conn.cursor()
        c.execute("SELECT * FROM technicians")
        technicians = c.fetchall()
        conn.close()

        if not technicians:
            st.write("No technicians available. Please check back later.")
            return

        page = st.number_input("Page", min_value=1, max_value=(len(technicians) - 1) // 4 + 1, step=1, value=1)
        start = (page - 1) * 4
        end = start + 4
        technicians_to_display = technicians[start:end]

        for i, tech in enumerate(technicians_to_display):
            col1, col2 = st.columns(2)
            with col1 if i % 2 == 0 else col2:
                st.write(f"### {tech[2]}")
                st.write(f"Phone: {tech[3]}")
                st.write(f"Address: {tech[4]}")
                st.write(f"Uploaded At: {tech[7]}")
                st.image(io.BytesIO(tech[5]), caption='Technician Photo', use_column_width=True)
                st.download_button(
                    "Download Technical Certificate",
                    data=tech[6],
                    file_name=f"{tech[2]}_Technical_Certificate.pdf",
                    key=f"download_{tech[0]}"
                )
                st.markdown(f'''
                    <a href="tel:{tech[3]}" target="_blank">
                        <button>Call {tech[2]}</button>
                    </a>
                ''', unsafe_allow_html=True)
                if st.button(f"Book {tech[2]}", key=f"book_{tech[0]}"):
                    st.success(f"Service booked with {tech[2]}. Call them at {tech[3]}")

# Function to delete technician (password protected)
def delete_technician():
    conn = get_db_connection('actual.db')
    if conn:
        c = conn.cursor()
        password = st.text_input("Enter Password", type="password")
        if password == "1234":  # Replace '1234' with your actual password
            st.success("Access granted")
            c.execute("SELECT id, name FROM technicians")
            technicians = c.fetchall()

            if not technicians:
                st.write("No technicians available to delete.")
                return

            selected_technician = st.selectbox(
                "Select Technician to Delete",
                technicians,
                format_func=lambda x: x[1]
            )

            if selected_technician:
                tech_id = selected_technician[0]
                if st.button(f"Delete {selected_technician[1]}", key=f"delete_{tech_id}"):
                    c.execute("DELETE FROM technicians WHERE id = ?", (tech_id,))
                    conn.commit()
                    st.success(f"Technician {selected_technician[1]} deleted.")
        else:
            st.error("Incorrect password")
        conn.close()

# Function to update technician details
def update_technician():
    conn = get_db_connection('actual.db')
    if conn:
        c = conn.cursor()
        c.execute("SELECT TechId, name FROM technicians")
        technicians = c.fetchall()
        conn.close()

        if not technicians:
            st.write("No technicians available to update.")
            return

        technician_ids = [tech[0] for tech in technicians]  # List of all TechIDs

        selected_technician_id = st.text_input("Enter Technician TechID to Update", "")

        if selected_technician_id and selected_technician_id in technician_ids:
            conn = get_db_connection('actual.db')
            if conn:
                c = conn.cursor()
                c.execute("SELECT * FROM technicians WHERE TechId = ?", (selected_technician_id,))
                tech = c.fetchone()
                conn.close()

                if tech:
                    with st.form("update_technician_form"):
                        name = st.text_input("Technician Name", value=tech[2])
                        phone = st.text_input("Phone Number", value=tech[3])
                        address = st.text_input("Address", value=tech[4])
                        photo = st.file_uploader("Upload New Photo (optional)", type=["jpeg", "jpg", "png"])
                        tech_certificate = st.file_uploader("Upload New Technical Certificate (optional)", type=["pdf"])
                        submit = st.form_submit_button("Update Technician")

                        if submit:
                            if name and phone and address:
                                uploaded_at = datetime.now().isoformat()

                                # Convert files to binary if uploaded
                                photo_data = photo.read() if photo else tech[5]
                                tech_certificate_data = tech_certificate.read() if tech_certificate else tech[6]

                                # Update database
                                conn = get_db_connection('actual.db')
                                if conn:
                                    c = conn.cursor()
                                    c.execute('''
                                        UPDATE technicians
                                        SET name = ?, phone = ?, address = ?, photo = ?, tech_certificate = ?, uploaded_at = ?
                                        WHERE TechId = ?
                                    ''', (name, phone, address, photo_data, tech_certificate_data, uploaded_at, selected_technician_id))
                                    conn.commit()
                                    conn.close()

                                    st.success(f"Technician {name}'s details updated.")
                            else:
                                st.error("Please fill in all the required fields")
                else:
                    st.error(f"Technician with TechId '{selected_technician_id}' not found.")
        elif selected_technician_id:
            st.error(f"Technician with TechId '{selected_technician_id}' not found or invalid input.")

def create_service_feed_table():
    conn = get_db_connection('service_feed.db')
    if conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS service_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tech_id TEXT,
                customer_email TEXT,
                booking_number TEXT,
                service_count INTEGER,
                problem_status TEXT,
                time_hours INTEGER,
                problem_area TEXT,
                user_feedback TEXT,
                spare_details TEXT,
                fees_paid TEXT,
                amount_paid REAL,
                timestamp TEXT
            )
        ''')
        conn.commit()
        conn.close()

def fill_technician_service_feed():
    create_service_feed_table()  # Ensure table exists before attempting to insert data
    conn = get_db_connection('service_feed.db')
    if conn:
        c = conn.cursor()
        with st.form("fill_service_feed_form"):
            tech_id = st.text_input("Technician TechID")
            customer_email = st.text_input("Customer Email")
            booking_number = st.text_input("Booking Number")
            service_count = st.number_input("Service Count", min_value=1, step=1)
            problem_status = st.selectbox("Problem Status", ["Call End", "Need Other Tech", "No one In Home", "Not Solved"])
            time_hours = st.number_input("Time in Hours", min_value=1, step=1)
            problem_area = st.text_area("Problem Area")
            user_feedback = st.text_area("User Feedback")
            spare_details = st.text_area("Spare Conjunction Details")
            fees_paid = st.selectbox("Fees Paid", ["Done", "Something", "No fees paid by Customer"])
            amount_paid = st.number_input("Amount Paid", min_value=0.0)
            submit = st.form_submit_button("Submit Service Feed")

            if submit:
                if tech_id and customer_email and problem_status and problem_area and user_feedback and spare_details and fees_paid:
                    timestamp = datetime.now().isoformat()

                    c.execute('''
                        INSERT INTO service_feed
                        (tech_id, customer_email, booking_number, service_count, problem_status, time_hours, problem_area, user_feedback, spare_details, fees_paid, amount_paid, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (tech_id, customer_email, booking_number, service_count, problem_status, time_hours, problem_area, user_feedback, spare_details, fees_paid, amount_paid, timestamp))
                    
                    conn.commit()
                    st.success("Service feed successfully submitted.")
                else:
                    st.error("Please fill in all the required fields.")
        conn.close()

if __name__ == "__main__":
    create_user_table()  # Ensure user table exists

    st.title("Technician Booking Service")

    # Sidebar menu including user and technician account creation options
    with st.sidebar:
        choice = option_menu(
            "Menu",
            ["Book Technician", "Upload Technician Details", "After Service Details", "Update Technician", "Delete Technician", "Sign Up", "Login"],
            icons=["Mobile", "cloud-upload", "Mobile", "pencil-square", "trash", "Mobile", "cloud-upload"],
            menu_icon="cast",
            default_index=0,
        )

    # Define boolean variables to track sign-up and login status
    signed_up = False
    logged_in = False

    # Check if the user is signed up and logged in before accessing other functionalities
    if choice not in ["Sign Up", "Login"]:
        # Check login status
        if st.session_state.logged_in:
            logged_in = True
        else:
            st.warning("Please log in first to access other functionalities.")
            choice = "Login"  # Redirect to login if not logged in

    if choice == "Sign Up":
        st.subheader("Sign Up")
        sign_up()
        # After successful sign-up, set signed_up to True
        if st.session_state.signed_up:
            signed_up = True

    elif choice == "Login":
        st.subheader("Login")
        login()
        # After successful login, set logged_in to True
        if st.session_state.logged_in:
            logged_in = True

    # Proceed to other functionalities only if logged in
    if logged_in:
        if choice == "Book Technician":
            st.subheader("Book a Technician")
            book_technician()
        elif choice == "Upload Technician Details":
            st.subheader("Upload Technician Details")
            upload_technician()
        elif choice == "Update Technician":
            st.subheader("Update Technician Details")
            update_technician()
        elif choice == "After Service Details":
            st.subheader("After Service Details")
            fill_technician_service_feed()
        elif choice == "Delete Technician":
            st.subheader("Delete Technician (Admin Only)")
            delete_technician()
