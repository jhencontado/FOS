import base64
import datetime
import os
import time

from datetime import datetime

import MySQLdb.cursors
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, current_app

from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import threading
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)


app.config['SECRET_KEY'] = os.urandom(24)
# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'dbadmin'
app.config['MYSQL_PASSWORD'] = 'Jheyan061709'
app.config['MYSQL_DB'] = 'library'



app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'booklight019@gmail.com'
app.config['MAIL_PASSWORD'] = 'iacv uvqd brme akst'
app.config['MAIL_DEFAULT_SENDER'] = 'booklight019@gmail.com'
mail = Mail(app)

app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3MB, adjust as needed
# Set upload folder
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


mysql = MySQL(app)
now = datetime.now()

@app.route('/home')
def home():
    return render_template('index.html')
@app.route('/')
def index():
    return render_template('index.html')


# Example route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        contact_number = request.form['contact_number']
        username = request.form['username']
        password = request.form['password']  # Store as plain text (for demo purposes, use hashed password in real apps)
        email = request.form['email']
        role = request.form['role']

        # Process the photo
        photo_data = request.form.get("photo", "")
        if photo_data:
            try:
                # Clean and decode the base64 image data
                photo_data = photo_data.replace("data:image/png;base64,", "")
                photo_bytes = base64.b64decode(photo_data)

                # Create a secure filename
                photo_filename = secure_filename(f"{username}.png")
                photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_filename)

                # Save the photo to the specified folder
                with open(photo_path, "wb") as f:
                    f.write(photo_bytes)

                print(f"Photo saved to: {photo_path}")  # Log the file path

            except Exception as e:
                print(f"Error processing photo: {e}")
                photo_filename = "default.png"  # Fallback image in case of error
        else:
            photo_filename = "default.png"  # Fallback if no photo is provided

        # Save the user data and photo filename into the database (pseudo code)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'INSERT INTO admin (name, contact_number, username, password, email, role, photo) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (name, contact_number, username, password, email, role, photo_filename)
        )
        mysql.connection.commit()
        cursor.close()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admin WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account and account['password'] == password:  # Compare passwords (consider hashing)
            session['loggedin'] = True
            session['admin_id'] = account['admin_id']
            session['username'] = account['username']
            session['role'] = account['role']
            session['admin_name'] = account['name']  # Store admin name in session

            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for('login'))  # ✅ Redirect instead of render

    return render_template('index.html')

# Book Page Route (after login)
@app.route('/book')
def book_page():
    if 'loggedin' in session:
        return render_template('book.html')
    else:
        flash("Please login first!", "danger")
        return redirect(url_for('login'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.context_processor
def inject_admin():
    if 'admin_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name, photo FROM admin WHERE admin_id = %s", (session['admin_id'],))
        admin = cur.fetchone()
        cur.close()

        if admin:
            name = admin[0] if admin[0] else "Admin"
            photo = admin[1] if admin[1] else "default.png"  # Default image if None

            print("Admin Photo Path:", photo)  # Debugging Line

            return {'name': name, 'photo': photo}

    return {'name': "Guest", 'photo': "default.png"}  # Default values when no admin is logged in



from MySQLdb.cursors import DictCursor

@app.route('/dashboard-data')
def dashboard_data():
    if 'admin_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    cur = mysql.connection.cursor(DictCursor)

    # Get basic stats
    cur.execute("SELECT COUNT(*) AS count FROM reader")
    registered_readers = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM book")
    total_books = cur.fetchone()['count']

    # Books currently issued = records in `issued` with no match in `return_book`
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM issued i
        LEFT JOIN return_book r ON i.issued_number = r.issued_number
        WHERE r.issued_number IS NULL
    """)
    issued_books = cur.fetchone()['count']

    # Overdue = not returned AND return_date is past today
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM issued i
        LEFT JOIN return_book r ON i.issued_number = r.issued_number
        WHERE r.issued_number IS NULL AND i.return_date < CURDATE()
    """)
    overdue_books = cur.fetchone()['count']

    # Latest readers
    cur.execute("""
        SELECT reader_id AS id, name, contact_number AS contact, email
        FROM reader
        WHERE status = 'active'
        ORDER BY reader_id DESC
        LIMIT 5
    """)
    readers = cur.fetchall()

    # Latest books
    cur.execute("""
        SELECT book_id AS id, title, author, available_qnty AS available
        FROM book
        ORDER BY book_id DESC
        LIMIT 5
    """)
    books = cur.fetchall()

    # Top picks
    cur.execute("""
        SELECT title, image
        FROM book
        WHERE available_qnty > 0
        ORDER BY book_id DESC
        LIMIT 8
    """)
    top_books = cur.fetchall()

    cur.close()

    # Optional debug
    print("Dashboard Data:", {
        'registeredReaders': registered_readers,
        'totalBooks': total_books,
        'issuedBooks': issued_books,
        'overdueBooks': overdue_books,
        'readers': readers,
        'books': books,
        'topBooks': top_books
    })

    return jsonify({
        'registeredReaders': registered_readers,
        'totalBooks': total_books,
        'issuedBooks': issued_books,
        'overdueBooks': overdue_books,
        'readers': readers,
        'books': books,
        'topBooks': top_books
    })

@app.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        print("Session does not contain admin_id")  # Debugging
        return "Unauthorized", 401

    try:
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT name, photo FROM admin WHERE admin_id = %s", (session['admin_id'],))
        admin_data = cur.fetchone()
        cur.close()

        if admin_data:
            return render_template(
                'dashboard.html',
                name=admin_data['name'],
                photo=admin_data['photo'],
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            return "Admin not found", 404
    except Exception as e:
        print(f"Error fetching admin data: {e}")
        return "Internal Server Error", 500


@app.route('/books', methods=['GET'])
def books():
    search_query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Updated query to show all books, even those with 0 availability
    if search_query:
        query = """
        SELECT *, CONCAT('₱', FORMAT(book_amount, 2)) AS book_amount_display 
        FROM book 
        WHERE title LIKE %s OR author LIKE %s OR genre LIKE %s
        """
        cursor.execute(query, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        query = "SELECT *, CONCAT('₱', FORMAT(book_amount, 2)) AS book_amount_display FROM book"
        cursor.execute(query)

    books = cursor.fetchall()

    # Fetch the count of lent books per reader (same logic as before)
    cursor.execute("""
    SELECT reader_id, COUNT(*) AS lend_count 
    FROM issued 
    GROUP BY reader_id
    """)
    lend_counts = cursor.fetchall()

    # Update each reader record with the lent book count
    for reader in lend_counts:
        cursor.execute("""
        UPDATE reader SET lend_book = %s WHERE reader_id = %s
        """, (reader['lend_count'], reader['reader_id']))

    mysql.connection.commit()
    cursor.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(books=books)

    return render_template('book.html', books=books, search_query=search_query)


@app.route('/add_book', methods=['POST'])
def add_book():
    try:
        data = request.form
        file = request.files.get('image')

        # ✅ Debugging: Print received form data
        print("Received Form Data:", data)

        cursor = mysql.connection.cursor()

        query = """
        INSERT INTO book (title, author, genre, publisher, year_publish, ISBN, available_qnty, book_amount, image) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        image_filename = file.filename if file else 'default.jpg'
        values = (
            data['title'], data['author'], data.get('genre', ''),
            data.get('publisher', ''), data['year_publish'],
            data['ISBN'], data['available_qnty'], data['book_amount'], image_filename
        )

        cursor.execute(query, values)
        mysql.connection.commit()  # ✅ Make sure to commit changes
        cursor.close()

        return jsonify({"message": "Book added successfully!"})

    except Exception as e:
        print("Error Adding Book:", str(e))  # ✅ Debugging: Print error message
        return jsonify({"error": str(e)}), 500

@app.route('/update_book', methods=['POST'])
def update_book():
    try:
        data = request.form
        file = request.files.get('image')

        # Debugging: Print received form data
        print("Received Update Data:", data)

        cursor = mysql.connection.cursor()

        # Check if an image was uploaded
        if file and file.filename:
            image_filename = file.filename
            query = """
            UPDATE book 
            SET title=%s, author=%s, genre=%s, publisher=%s, 
                year_publish=%s, ISBN=%s, available_qnty=%s, book_amount=%s, image=%s
            WHERE book_id=%s
            """
            values = (
                data['title'], data['author'], data.get('genre', ''),
                data.get('publisher', ''), data['year_publish'],
                data['ISBN'], data['available_qnty'], data['book_amount'], image_filename, data['book_id']
            )
        else:
            query = """
            UPDATE book 
            SET title=%s, author=%s, genre=%s, publisher=%s, 
                year_publish=%s, ISBN=%s, available_qnty=%s, book_amount=%s
            WHERE book_id=%s
            """
            values = (
                data['title'], data['author'], data.get('genre', ''),
                data.get('publisher', ''), data['year_publish'],
                data['ISBN'], data['available_qnty'], data['book_amount'], data['book_id']
            )

        cursor.execute(query, values)
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Book updated successfully!"})

    except Exception as e:
        print("Error Updating Book:", str(e))
        return jsonify({"error": str(e)}), 500


# ✅ Delete a book
@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM book WHERE book_id = %s", (book_id,))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"message": "Book deleted successfully!"})

@app.route('/readers', methods=['GET'])
def readers():
    update_reader_lend_status()
    search_query = request.args.get('search', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    base_query = """
       SELECT 
           r.reader_id,
           r.name,
           r.contact_number,
           r.reference_id,
           r.address,
           r.email,
           r.status,
           r.lend_book
       FROM reader r
       WHERE 1=1
       """
    filters = []
    params = []

    if search_query:
        filters.append("(r.name LIKE %s OR r.contact_number LIKE %s OR r.reference_id LIKE %s)")
        params.extend([f"%{search_query}%"] * 3)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += " GROUP BY r.reader_id"

    cursor.execute(base_query, tuple(params))
    readers = cursor.fetchall()
    cursor.close()

    # If it's an AJAX request or a search, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or search_query:
        return jsonify(readers=readers)

    return render_template('reader.html', readers=readers)



def update_reader_lend_status():
    cursor = mysql.connection.cursor()

    # Update readers who still have unreturned books
    cursor.execute("""
        UPDATE reader r
        JOIN (
            SELECT i.reader_id, COUNT(*) AS lent_count
            FROM issued i
            LEFT JOIN return_book rb ON i.issued_number = rb.issued_number
            WHERE rb.issued_number IS NULL
            GROUP BY i.reader_id
        ) i ON r.reader_id = i.reader_id
        SET 
            r.lend_book = i.lent_count,
            r.status = CASE 
                         WHEN i.lent_count >= 5 THEN 'inactive' 
                         ELSE 'active'
                       END
    """)

    # Reset readers who have returned all books
    cursor.execute("""
        UPDATE reader
        SET lend_book = 0, status = 'active'
        WHERE reader_id NOT IN (
            SELECT reader_id FROM issued
            WHERE issued_number NOT IN (
                SELECT issued_number FROM return_book
            )
        )
    """)

    mysql.connection.commit()
    cursor.close()


# Handle large requests (413 Error Handling)
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File is too large. Please upload a smaller file."}), 413

@app.route('/add_reader', methods=['POST'])
def add_reader():
    try:
        name = request.form['name']
        contact_number = request.form['contact_number']
        reference_id = request.form['reference_id']
        address = request.form['address']
        email = request.form['email']
        photo_data = request.form['photo']  # Base64 image data

        # Check if photo data is available and validate its size
        if photo_data:
            # Check the size of the base64 image data (1 MB max here)
            max_size = 1 * 1024 * 1024  # 1 MB limit for image
            if len(photo_data) > max_size:
                return jsonify({"error": "The photo is too large. Please capture a smaller photo."}), 413

            # Convert Base64 to an image file
            photo_filename = f"{name.replace(' ', '_')}.png"
            photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_filename)

            # Save the image as a file in the upload folder
            with open(photo_path, "wb") as fh:
                fh.write(base64.b64decode(photo_data.split(",")[1]))

        else:
            # Use a default image if no photo is uploaded
            photo_filename = "default.png"

        # Insert into database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO reader (name, contact_number, reference_id, address, email, photo) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, contact_number, reference_id, address, email, photo_filename))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Reader registered successfully!"})


    except Exception as e:

        print(f"Error registering reader: {e}")  # Optional logging

        return jsonify({"error": str(e)}), 500


@app.route('/delete_reader/<int:reader_id>', methods=['POST'])
def delete_reader(reader_id):
    try:
        cursor = mysql.connection.cursor()
        query = "DELETE FROM reader WHERE reader_id = %s"
        cursor.execute(query, (reader_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Reader deleted successfully!"})
    except Exception as e:
        print("Error deleting reader:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/update_reader', methods=['POST'])
def update_reader():
    try:
        # Capture the form data
        reader_id = request.form['reader_id']
        name = request.form['name']
        contact_number = request.form['contact_number']
        reference_id = request.form['reference_id']
        address = request.form['address']
        email = request.form['email']

        # Log data to ensure it's being received
        print(f"Received data: {reader_id}, {name}, {contact_number}, {reference_id}, {address}, {email}")

        # Connect to the database
        cursor = mysql.connection.cursor()

        # Update query
        query = """
        UPDATE reader
        SET name = %s, contact_number = %s, reference_id = %s, address = %s, email = %s
        WHERE reader_id = %s
        """

        # Execute the query
        cursor.execute(query, (name, contact_number, reference_id, address, email, reader_id))
        mysql.connection.commit()
        cursor.close()

        # Success response
        return jsonify({"message": "Reader updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_reader/<int:reader_id>')
def get_reader(reader_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM reader WHERE reader_id = %s", (reader_id,))
    reader = cursor.fetchone()
    cursor.close()
    return jsonify(reader)

@app.route('/deactivate_reader/<int:reader_id>', methods=['POST'])
def deactivate_reader(reader_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE reader SET status = 'inactive' WHERE reader_id = %s", (reader_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('manage_readers'))

@app.route('/issue', methods=['GET'])
def issue_page():
    return render_template('issue.html')
@app.route('/search_reader', methods=['GET'])
def search_reader():
    query = request.args.get('query', '')
    if query:
        try:
            cursor = mysql.connection.cursor()
            # Use subquery to count only books that are NOT returned
            cursor.execute("""
                           SELECT 
                               r.reader_id, r.name, r.email, r.contact_number, r.status,
                               (
                                   SELECT COUNT(*) FROM issued i
                                   LEFT JOIN return_book rb ON i.issued_number = rb.issued_number
                                   WHERE i.reader_id = r.reader_id AND rb.issued_number IS NULL
                               ) AS lend_book
                           FROM reader r
                           WHERE r.name LIKE %s OR r.reader_id LIKE %s
                       """, (f"%{query}%", f"%{query}%"))

            readers = cursor.fetchall()
            cursor.close()

            # Format result into JSON
            reader_data = []
            for reader in readers:
                reader_data.append({
                    'reader_id': reader[0],
                    'name': reader[1],
                    'email': reader[2],
                    'contact_number': reader[3],
                    'status': reader[4],
                    'lend_book': reader[5]
                })

            return jsonify(reader_data)
        except Exception as e:
            print(f"Error during reader search: {e}")
            return jsonify({'error': 'An error occurred while fetching reader data'}), 500
    return jsonify([])

@app.route('/fetch_books', methods=['GET'])
def fetch_books():
    cur = mysql.connection.cursor()
    cur.execute("SELECT book_id, title, author, image FROM book WHERE available_qnty > 0")
    books = cur.fetchall()
    cur.close()

    # Manually map MySQL rows to dictionaries if needed
    book_list = []
    for book in books:
        book_list.append({
            'book_id': book[0],
            'title': book[1],
            'author': book[2],
            'image': book[3]
        })

    return jsonify(book_list)

@app.route('/get_reader_status/<int:reader_id>', methods=['GET'])
def get_reader_status(reader_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT status
        FROM reader
        WHERE reader_id = %s
    """, (reader_id,))
    status = cursor.fetchone()
    cursor.close()

    if status:
        return jsonify({"status": status[0]})
    else:
        return jsonify({"status": "inactive"})  # Return 'inactive' if reader does not exist


@app.route('/issue_books', methods=['POST'])
def issue_books():
    data = request.json
    reader_id = data.get('reader_id')
    books = data.get('books')
    start_date = data.get('start_date')
    return_date = data.get('return_date')
    admin_id = data.get('admin_id')  # Capture admin ID from request
    fine_type = data.get('fine_type')
    fine_amount = data.get('fine_amount')

    cur = mysql.connection.cursor()

    # Generate a short transaction ID (you can use a timestamp for simplicity)
    transaction_id = str(int(time.time()))  # Shortened version

    issued_numbers = []
    book_titles = []

    for book_id in books:
        cur.execute("SELECT title FROM book WHERE book_id = %s", (book_id,))
        book_title = cur.fetchone()
        if book_title:
            book_titles.append(book_title[0])  # Append book title to the list

        # Insert into issued books table
        cur.execute("""
            INSERT INTO issued (reader_id, book_id, start_date, return_date, transaction_id, admin_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (reader_id, book_id, start_date, return_date, transaction_id, admin_id))

        issued_number = cur.lastrowid
        issued_numbers.append(issued_number)

        update_reader_lend_status()

    # Fine logic: Check if the return date is overdue
    from datetime import datetime

    fine_details = None
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    return_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
    overdue_days = (return_date_obj - start_date_obj).days

    # If the return date is overdue by more than 7 days, calculate fine
    if overdue_days > 7:
        fine_amount = (overdue_days - 7) * 20  # Fine of 20 per day after 7 days
        fine_details = {
            'fine_type': fine_type,
            'fine_amount': round(fine_amount, 2),
            'status': 'unpaid'
        }

        # Insert into fine table
        cur = mysql.connection.cursor()
        cur.execute("""
                INSERT INTO fine (reader_id, fine_type, fine_amount, status, issued_date)
                VALUES (%s, %s, %s, %s, CURDATE())
            """, (reader_id, fine_details['fine_type'], fine_details['fine_amount'], fine_details['status']))

    # Fetch reader info for email
    cur.execute("SELECT name, email, contact_number FROM reader WHERE reader_id = %s", (reader_id,))
    reader_data = cur.fetchone()
    reader_name = reader_data[0] if reader_data else "Unknown"
    reader_email = reader_data[1] if reader_data else None
    reader_contact = reader_data[2] if reader_data else "Unknown"



    # Fetch admin name for the receipt
    cur.execute("SELECT name FROM admin WHERE admin_id = %s", (admin_id,))
    admin_name = cur.fetchone()
    admin_name = admin_name[0] if admin_name else "Unknown"

    # Fetch reader name and contact details
    cur.execute("SELECT name, contact_number FROM reader WHERE reader_id = %s", (reader_id,))
    reader_data = cur.fetchone()
    reader_name = reader_data[0] if reader_data else "Unknown"
    reader_contact = reader_data[1] if reader_data else "Unknown"

    mysql.connection.commit()
    cur.close()

    # Prepare session data
    session['receipt_data'] = {
        "transaction_id": transaction_id,
        "admin": {
            "id": admin_id,
            "name": admin_name
        },
        "reader": {
            "id": reader_id,
            "name": reader_name,
            "contact": reader_contact
        },
        "start_date": start_date,
        "return_date": return_date,
        "books": [{"title": title} for title in book_titles],
        "fine_details": fine_details  # Add fine details if any
    }
    # Send email
    if reader_email:
        send_issue_email(reader_email, reader_name, book_titles, return_date)

    # Inside your return or issue route after email is sent successfully
    flash("Email sent to reader successfully!", "success")


    # Debugging session data before returning it
    print(session['receipt_data'])

    return jsonify({
        "receipt_url": "/receipt",  # Optional: You can redirect the user to this URL after issuing books
        "receipt": session['receipt_data']  # Send the receipt as part of the response
    })

def get_title_by_id(book_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT title FROM book WHERE book_id = %s", (book_id,))
    row = cur.fetchone()
    return row[0] if row else 'Unknown Title'

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ Email sent to {msg.recipients}")
        except Exception as e:
            print(f"❌ Email failed to send: {str(e)}")



def send_issue_email(reader_email, reader_name, book_titles, return_date):
    from flask_mail import Message
    from flask import current_app

    book_list_html = ''.join(f"<li>{title}</li>" for title in book_titles)
    msg = Message(
        subject="📚 Book Issued - BookLight Notification",
        sender="booklight019@gmail.com",
        recipients=[reader_email]
    )
    msg.html = f"""
        <h3>Hello {reader_name},</h3>
        <p>You have borrowed the following books from BookLight:</p>
        <ul>{book_list_html}</ul>
        <p><strong>Return Date:</strong> {return_date}</p>
        <p>Please ensure to return them on or before the due date to avoid fines.</p>
        <br>
        <p>Best regards,<br>📘 BookLight Library Team</p>
    """

    # Use current_app inside a background thread
    app = current_app._get_current_object()
    threading.Thread(target=send_async_email, args=(app, msg)).start()




@app.route('/receipt', methods=['GET'])
def receipt():
    receipt_data = session.get('receipt_data')  # Ensure receipt data is stored in session
    if not receipt_data:
        return "No receipt data available", 400
    return render_template('receipt.html', receipt=receipt_data)



@app.route('/get_logged_in_admin', methods=['GET'])
def get_logged_in_admin():
    # Assuming session-based authentication
    admin_id = session.get('admin_id')

    if admin_id:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT admin_id, name
                FROM admin
                WHERE admin_id = %s
            """, (admin_id,))
            admin = cursor.fetchone()

            # Ensure the cursor is closed even in case of an exception
            cursor.close()

            if admin:
                return jsonify({
                    "admin_id": admin[0],
                    "admin_name": admin[1]
                })
            else:
                return jsonify({"error": "Admin not found"}), 404
        except Exception as e:
            print(f"Error fetching admin details: {e}")
            return jsonify({"error": "An error occurred while fetching admin details"}), 500
    else:
        return jsonify({"error": "Admin not logged in"}), 401



@app.route('/update_fine_status', methods=['POST'])
def update_fine_status():
    data = request.json
    fine_id = data.get('fine_id')
    new_status = data.get('new_status')  # Either 'paid' or 'unpaid'

    # Ensure the new status is either 'paid' or 'unpaid'
    if new_status not in ['paid', 'unpaid']:
        return jsonify({"error": "Invalid fine status."}), 400

    # Update the fine status in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE fine SET status = %s WHERE fine_id = %s", (new_status, fine_id))

    # Commit changes
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Fine status updated successfully!"}), 200


@app.route('/fetch_book_price', methods=['GET'])
def fetch_book_price():
    book_id = request.args.get('book_id')

    if not book_id:
        return jsonify({'error': 'Book ID is required'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT book_amount FROM book WHERE book_id = %s", (book_id,))
        book = cur.fetchone()
        cur.close()

        if book:
            return jsonify({'book_amount': float(book[0])})
        else:
            return jsonify({'error': 'Book not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fetch_issued', methods=['GET'])
def fetch_issued():
    search_query = request.args.get('search', '')
    filter_overdue = request.args.get('overdue') == 'true'
    filter_exceed_lent = request.args.get('exceed_lent') == 'true'

    cur = mysql.connection.cursor()

    query = f"""
        SELECT 
            issued.issued_number, issued.reader_id, reader.name, issued.book_id, 
            book.title, issued.start_date, issued.return_date, issued.transaction_id,
            reader.status,
            (
                SELECT COUNT(*) 
                FROM issued AS i2 
                WHERE i2.reader_id = issued.reader_id
                AND NOT EXISTS (
                    SELECT 1 
                    FROM return_book rb2 
                    WHERE rb2.issued_number = i2.issued_number
                )
            ) AS total_borrowed,
            issued.email_sent
        FROM issued
        JOIN reader ON issued.reader_id = reader.reader_id
        JOIN book ON issued.book_id = book.book_id
        WHERE (reader.name LIKE %s OR issued.reader_id LIKE %s)
        AND NOT EXISTS (
            SELECT 1
            FROM return_book rb
            WHERE rb.issued_number = issued.issued_number
        )
    """

    # Append optional conditions
    conditions = []
    if filter_overdue:
        conditions.append("issued.return_date < CURDATE()")
    if filter_exceed_lent:
        conditions.append("""
            (
                SELECT COUNT(*) 
                FROM issued i2 
                WHERE i2.reader_id = issued.reader_id
                AND NOT EXISTS (
                    SELECT 1 
                    FROM return_book rb2 
                    WHERE rb2.issued_number = i2.issued_number
                )
            ) >= 5
        """)

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY issued.issued_number DESC"

    try:
        cur.execute(query, (f"%{search_query}%", f"%{search_query}%"))
        issued_books = cur.fetchall()
        if not issued_books:
            return jsonify([])  # return empty list instead of 404 for frontend ease
    except Exception as e:
        print(f"Error fetching issued books: {e}")
        return jsonify({"error": "An error occurred while fetching issued books."}), 500
    finally:
        cur.close()

    # Build JSON response
    issued_books_list = [
        {
            "issued_number": row[0],
            "reader_id": row[1],
            "name": row[2],
            "book_id": row[3],
            "title": row[4],
            "start_date": row[5].strftime('%Y-%m-%d'),
            "return_date": row[6].strftime('%Y-%m-%d'),
            "transaction_id": row[7],
            "status": row[8],
            "total_borrowed": row[9],
            "email_sent": bool(row[10])
        }
        for row in issued_books
    ]

    return jsonify(issued_books_list)

@app.route('/fetch_transaction_details', methods=['GET'])
def fetch_transaction_details():
    transaction_id = request.args.get('transaction_id')

    if not transaction_id:
        return jsonify({"error": "Transaction ID is required"}), 400

    try:
        cur = mysql.connection.cursor()

        query = """
        SELECT issued.issued_number, issued.reader_id, reader.name, reader.email, 
               reader.contact_number, reader.photo, 
               book.title, book.author, book.genre, book.publisher, 
               issued.start_date, issued.return_date, issued.transaction_id, issued.admin_id
        FROM issued
        JOIN reader ON issued.reader_id = reader.reader_id
        JOIN book ON issued.book_id = book.book_id
        WHERE issued.transaction_id = %s
        """

        cur.execute(query, (transaction_id,))
        transaction = cur.fetchone()

        if transaction:
            transaction_details = {
                "reader": {
                    "name": transaction[2],
                    "email": transaction[3],
                    "contact_number": transaction[4],
                    "photo": transaction[5] if transaction[5] else "default_photo.jpg",  # Ensure default exists or handle accordingly
                },
                "book": {
                    "title": transaction[6],
                    "author": transaction[7],
                    "genre": transaction[8],
                    "publisher": transaction[9]
                },
                "admin_id": transaction[12],
                "start_date": transaction[10].strftime('%Y-%m-%d'),
                "return_date": transaction[11].strftime('%Y-%m-%d'),
                "transaction_id": transaction[12]
            }
            return jsonify(transaction_details)
        else:
            return jsonify({"error": "Transaction not found"}), 404

    except Exception as e:
        print(f"Error fetching transaction details: {e}")
        return jsonify({"error": "An error occurred while fetching transaction details"}), 500
    finally:
        cur.close()

@app.route('/fetch_reader/<int:reader_id>')
def fetch_reader(reader_id):
    reader = readers.get(reader_id, {})
    return jsonify(reader)

@app.route('/list_issued')
def list_issued():
    return render_template('list_issued.html')


@app.route('/return')
def return_books():
    admin_id = session.get('admin_id')
    return render_template('return.html')


@app.route('/fetch_return', methods=['GET'])
def fetch_return():
    search_query = request.args.get('search', '')
    cur = mysql.connection.cursor()
    query = """
    SELECT i.issued_number, r.reader_id, r.name, b.book_id, b.title, i.return_date,
           DATEDIFF(CURDATE(), i.return_date) AS exceed_days,
           IF(DATEDIFF(CURDATE(), i.return_date) > 0, DATEDIFF(CURDATE(), i.return_date) * 50, 0) AS fine
    FROM issued i
    JOIN reader r ON i.reader_id = r.reader_id
    JOIN book b ON i.book_id = b.book_id
    WHERE (r.name LIKE %s OR r.reader_id LIKE %s)
    AND i.issued_number NOT IN (SELECT issued_number FROM return_book)
    """
    cur.execute(query, (f"%{search_query}%", f"%{search_query}%"))
    data = cur.fetchall()
    cur.close()

    issued_books = []
    for row in data:
        issued_books.append({
            'issued_number': row[0],
            'reader_id': row[1],
            'name': row[2],
            'book_id': row[3],
            'title': row[4],
            'return_date': row[5].strftime('%Y-%m-%d'),
            'exceed_days': max(0, row[6]),
            'fine': row[7]
        })
    return jsonify(issued_books)


@app.route('/process_return', methods=['POST'])
def process_return():
    try:
        data = request.get_json()
        issued_number = data.get('issued_number')
        book_condition = data.get('book_condition', 'good')  # Default to 'good'
        raw_fine_type = data.get('fine_type', 'overdue')

        # Normalize fine_type to valid values (None if invalid)
        fine_type = None if raw_fine_type == 'none' else raw_fine_type

        # Ensure the admin is logged in (using session)
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Admin not logged in'}), 401  # Unauthorized

        cur = mysql.connection.cursor()

        # Fetch issued book details
        cur.execute("SELECT reader_id, book_id, return_date FROM issued WHERE issued_number = %s", (issued_number,))
        issued_data = cur.fetchone()

        if not issued_data:
            return jsonify({'message': 'Issued record not found'}), 404

        reader_id, book_id, return_date = issued_data

        # Ensure return_date is today's date when returned
        today_date = datetime.today().date()

        # Handle return_date (ensure it is a date object)
        if isinstance(return_date, str):
            return_date = datetime.strptime(return_date, '%Y-%m-%d').date()

        # Calculate exceed days (if any)
        exceed_days = max(0, (today_date - return_date).days)

        # Fine Calculation
        if fine_type not in ['overdue', 'lost', 'damaged']:
            fine_type = None
            fine = 0
            print("No fine type matched, fine set to 0.")
        else:
            if fine_type == 'overdue':
                fine = exceed_days * 50
                print(f"Overdue fine calculated: {fine} for {exceed_days} exceed days.")
            elif fine_type == 'lost':
                cur.execute("SELECT book_amount FROM book WHERE book_id = %s", (book_id,))
                book_data = cur.fetchone()
                fine = book_data[0] if book_data else 0
                print(f"Lost fine calculated: {fine} from book price.")
            elif fine_type == 'damaged':
                fine = 100
                print(f"Damaged fine set: {fine}")

        fine_amount = float(data.get('fine_amount', fine))  # Default to calculated fine
        fine_status = data.get('fine_status') or 'unpaid'  # Default to 'unpaid'
        # Insert into return_book table
        cur.execute(""" 
            INSERT INTO return_book (issued_number, reader_id, book_id, return_date, book_condition, 
                                     fine_type, fine_amount, fine_status, processed_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (issued_number, reader_id, book_id, today_date, book_condition, fine_type, fine, fine_status, admin_id))

        # Fetch the return_id generated by the insert query
        cur.execute("SELECT LAST_INSERT_ID()")
        return_id = cur.fetchone()[0]

        # Update the available quantity in the book table
        cur.execute("UPDATE book SET available_qnty = available_qnty + 1 WHERE book_id = %s", (book_id,))

        # Update the lend_book count in the reader table
        cur.execute("UPDATE reader SET lend_book = lend_book - 1 WHERE reader_id = %s", (reader_id,))

        # Check if lend_book count is less than 5, update status to 'active'
        cur.execute("SELECT lend_book FROM reader WHERE reader_id = %s", (reader_id,))
        lend_book_count = cur.fetchone()

        if lend_book_count and lend_book_count[0] < 5:
            cur.execute("UPDATE reader SET status = 'active' WHERE reader_id = %s", (reader_id,))

        # Commit changes to the database
        mysql.connection.commit()

        # Fetch names and contact/email
        cur.execute("SELECT name, contact_number, email FROM reader WHERE reader_id = %s", (reader_id,))
        reader_data = cur.fetchone()
        reader_name = reader_data[0] if reader_data else "Unknown"
        reader_contact = reader_data[1] if reader_data else "Unknown"
        reader_email = reader_data[2] if reader_data else None

        # Fetch book title
        cur.execute("SELECT title FROM book WHERE book_id = %s", (book_id,))
        book_data = cur.fetchone()
        book_title = book_data[0] if book_data else "Unknown"

        # Fetch admin name
        cur.execute("SELECT name FROM admin WHERE admin_id = %s", (admin_id,))
        admin_data = cur.fetchone()
        admin_name = admin_data[0] if admin_data else "Unknown"

        # Store return receipt details in session after processing
        session['return_receipt_data'] = {
            "return_id": return_id,
            "transaction_id": "T" + str(return_id),  # You can generate a custom transaction ID here
            "admin": {
                "id": admin_id,
                "name": admin_name
            },
            "reader": {
                "id": reader_id,
                "name": reader_name,
                "contact": reader_contact
            },
            "book": {
                "title": book_title
            },
            "return_date": return_date,
            "fine_details": {
                "amount": fine_amount,
                "type": fine_type,
                "status": fine_status
            }
        }

        # Send return confirmation email (only if email exists)
        if reader_email:
            send_return_email(
                reader_email=reader_email,
                reader_name=reader_name,
                book_title=book_title,
                return_date=today_date.strftime('%Y-%m-%d'),
                fine_amount=fine_amount,
                fine_type=fine_type,
                fine_status=fine_status
            )
        update_reader_lend_status()
        # Optional: return JSON to trigger frontend opening return_receipt
        return jsonify({
            "receipt_url": "/return_receipt",
            "receipt": session['return_receipt_data']
        })

    except Exception as e:
        # Rollback in case of an error
        mysql.connection.rollback()

        print(f"Error occurred during return processing: {str(e)}")  # Log the error

        return jsonify({'error': 'An error occurred: ' + str(e)}), 500


def send_return_email(reader_email, reader_name, book_title, return_date, fine_amount, fine_type, fine_status):
    from flask_mail import Message
    from flask import current_app

    msg = Message(
        subject="✅ Book Returned - BookLight Confirmation",
        sender="booklight019@gmail.com",
        recipients=[reader_email]
    )
    msg.html = f"""
        <h3>Hello {reader_name},</h3>
        <p>Thank you for returning the book:</p>
        <ul><li><strong>{book_title}</strong></li></ul>
        <p><strong>Return Date:</strong> {return_date}</p>
        <p><strong>Fine Details:</strong></p>
        <ul>
            <li>Type: {(fine_type or 'None').capitalize()}</li>
            <li>Amount: ₱{fine_amount:.2f}</li>
            <li>Status: {(fine_status or 'None').capitalize()}</li>
        </ul>
        <p>If you have any concerns about this transaction, feel free to contact us.</p>
        <br>
        <p>Warm regards,<br>📘 BookLight Library Team</p>
    """

    app = current_app._get_current_object()
    threading.Thread(target=send_async_email, args=(app, msg)).start()


@app.route('/return_receipt')
def return_receipt():
    receipt_data = session.get('return_receipt_data')  # Retrieve data from the session
    if not receipt_data:
        return "No return receipt data available", 400  # Return an error if no data found
    return render_template('return_receipt.html', receipt=receipt_data)  # Pass the data to the template





# Function to build the email content
def build_email_content(name, books_info):
    book_items = ''
    for book in books_info:
        title = book['title']
        overdue_days = book['overdue_days']
        fine = book['fine']
        overdue_message = f"Overdue by {overdue_days} days" if overdue_days > 0 else "Due Today"
        fine_message = f"Fine: ₱{fine}" if fine > 0 else "No fine"

        book_items += f"""
            <li>
                <strong>{title}</strong><br>
                {overdue_message}<br>
                {fine_message}
            </li>
        """

    return f"""
        <h3>Hi {name},</h3>
        <p>You have borrowed the following books from <strong>BookLight</strong>:</p>
        <ul>{book_items}</ul>
        <p>📘 BookLight Library Team</p>
    """

@app.route('/reminder/send_bulk_reminders', methods=['POST'])
def send_bulk_reminders():
    """Sends reminder emails to readers who have overdue books or have borrowed 5+ books."""
    cur = mysql.connection.cursor()

    # Fetch all issued books where email_sent is FALSE
    cur.execute("""
        SELECT 
            i.issued_number,
            i.reader_id,
            r.name,
            r.email,
            b.title,
            i.return_date,
            DATEDIFF(CURDATE(), i.return_date) AS overdue_days
        FROM issued i
        JOIN reader r ON i.reader_id = r.reader_id
        JOIN book b ON b.book_id = i.book_id
        WHERE i.email_sent = FALSE
    """)
    results = cur.fetchall()

    if not results:
        cur.close()
        return jsonify({"status": "No readers to notify"}), 200

    app = current_app._get_current_object()
    readers_dict = {}

    # Group issued books per reader
    for issued_number, reader_id, name, email, title, return_date, overdue_days in results:
        if not email:
            continue

        fine = max(0, overdue_days) * 50

        if reader_id not in readers_dict:
            readers_dict[reader_id] = {
                "name": name,
                "email": email,
                "books": [],
                "issued_numbers": []
            }

        readers_dict[reader_id]["books"].append({
            "title": title,
            "overdue_days": overdue_days,
            "fine": fine
        })
        readers_dict[reader_id]["issued_numbers"].append(issued_number)

    # Send email and update issued rows
    for reader_id, info in readers_dict.items():
        name = info["name"]
        email = info["email"]
        books_info = info["books"]
        issued_numbers = info["issued_numbers"]

        try:
            msg = Message(
                subject="⏰ Reminder - BookLight Library",
                sender="booklight019@gmail.com",
                recipients=[email]
            )
            msg.html = build_email_content(name, books_info)

            threading.Thread(target=send_async_email, args=(app, msg)).start()

            for issued_number in issued_numbers:
                cur.execute("UPDATE issued SET email_sent = TRUE WHERE issued_number = %s", (issued_number,))

            print(f"✅ Email queued for {name} ({email})")

        except Exception as e:
            print(f"❌ Failed to send email to {email}: {str(e)}")

    mysql.connection.commit()
    cur.close()

    return jsonify({"status": "📬 Emails sent successfully"}), 200


@app.route('/test_email')
def test_email():
    try:
        msg = Message(
            subject="Test Email from BookLight 📬",
            recipients=["jbdianzon@gmail.com"],  # replace with your own email
            body="This is a test email from BookLight Library system."
        )
        mail.send(msg)
        return "✅ Test email sent!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True)