import streamlit as st
from datetime import datetime
import sqlite3
import io
from streamlit_option_menu import option_menu

# Function to create database connection
def get_db_connection():
    try:
        conn = sqlite3.connect('actual.db')  # Changed database name to actual.db
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {e}")
        return None

# Function to create technicians table
def create_technicians_table():
    conn = get_db_connection()
    if conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                TechId TEXT UNIQUE,
                name TEXT,
                phone TEXT,
                address TEXT,
                photo BLOB,
                tech_certificate BLOB,
                uploaded_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

# Function to upload technician details
def upload_technician():
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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
            conn = get_db_connection()
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
                                conn = get_db_connection()
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


# Main block
if __name__ == "__main__":
    st.title("Technician Booking Service")

    # Create technicians table if it doesn't exist
    create_technicians_table()

    # Sidebar menu
    with st.sidebar:
        choice = option_menu(
            "Menu",
            ["Book Technician", "Upload Technician Details", "Delete Technician", "Update Technician"],
            icons=["Mobile", "cloud-upload", "trash", "pencil-square"],
            menu_icon="cast",
            default_index=0,
        )

    if choice == "Book Technician":
        st.subheader("Book a Technician")
        book_technician()
    elif choice == "Upload Technician Details":
        st.subheader("Upload Technician Details")
        upload_technician()
    elif choice == "Delete Technician":
        st.subheader("Delete Technician (Admin Only)")
        delete_technician()
    elif choice == "Update Technician":
        st.subheader("Update Technician Details")
        update_technician()
