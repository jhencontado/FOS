import datetime

import bcrypt
from flask import Flask, render_template,jsonify, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime
import time
import MySQLdb.cursors

import os



app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'dbadmin'
app.config['MYSQL_PASSWORD'] = 'Jheyan061709'
app.config['MYSQL_DB'] = 'library'

mysql = MySQL(app)
#today_date = datetime.date.today()
#app.secret_key = 'your_secret_key'

@app.route('/home')
def home():
    return render_template('index.html')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        contact_number = request.form['contact_number']
        username = request.form['username']
        password = request.form['password']  # Store as plain text
        email = request.form['email']
        role = request.form['role']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'INSERT INTO admin (name, contact_number, username, password, email, role) VALUES (%s, %s, %s, %s, %s, %s)',
            (name, contact_number, username, password, email, role)
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


@app.route('/dashboard-data')
def dashboard_data():
    cur = mysql.connection.cursor()

    # Get the count of registered readers
    cur.execute("SELECT COUNT(*) FROM reader")
    registered_readers = cur.fetchone()[0]

    # Get the total books count
    cur.execute("SELECT COUNT(*) FROM book")
    total_books = cur.fetchone()[0]

    # Get the issued books count
    cur.execute("SELECT COUNT(*) FROM issued")
    issued_books = cur.fetchone()[0]

    # Get the overdue books count (books that should have been returned)
    cur.execute("SELECT COUNT(*) FROM issued WHERE return_date < CURDATE()")
    overdue_books = cur.fetchone()[0]

    # Get latest readers list
    cur.execute("SELECT reader_id, name, contact_number, email FROM reader ORDER BY reader_id DESC LIMIT 5")
    readers = cur.fetchall()

    # Get latest books list
    cur.execute("SELECT book_id, title, author, available_qnty, image FROM book ORDER BY book_id DESC LIMIT 5")
    books = cur.fetchall()

    # Get top picks books (you can modify the logic here)
    cur.execute("SELECT book_id, title, image FROM book ORDER BY RAND() LIMIT 5")
    top_books = cur.fetchall()

    cur.close()

    return jsonify({
        "registeredReaders": registered_readers,
        "totalBooks": total_books,
        "issuedBooks": issued_books,
        "overdueBooks": overdue_books,
        "readers": [{"id": r[0], "name": r[1], "contact": r[2], "email": r[3]} for r in readers],
        "books": [{"id": b[0], "title": b[1], "author": b[2], "available": b[3]} for b in books],
        "topBooks": [{"id": tb[0], "title": tb[1], "image": tb[2]} for tb in top_books]  # Include images
    })


@app.route('/dashboard')
def dashboard():
    if 'admin_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name FROM admin WHERE admin_id = %s", (session['admin_id'],))
        admin_name = cur.fetchone()[0]  # Fetch the admin's name
        cur.close()
        return render_template('dashboard.html', name=admin_name)
    return "Unauthorized", 401



#@app.route("/book")
#def manage_books():harper lee
   # return render_template("book.html")
@app.route('/books', methods=['GET'])
def books():
    search_query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search_query:
        query = """
        SELECT * FROM book 
        WHERE available_qnty > 0 AND 
              (title LIKE %s OR author LIKE %s OR genre LIKE %s)
        """
        cursor.execute(query, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        query = "SELECT * FROM book WHERE available_qnty > 0"
        cursor.execute(query)

    books = cursor.fetchall()

    # Update reader table with the count of lent books
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

    mysql.connection.commit()  # Commit the changes
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
        INSERT INTO book (title, author, genre, publisher, year_publish, ISBN, available_qnty, image) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        image_filename = file.filename if file else 'default.jpg'
        values = (
            data['title'], data['author'], data.get('genre', ''),
            data.get('publisher', ''), data['year_publish'],
            data['ISBN'], data['available_qnty'], image_filename
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
                year_publish=%s, ISBN=%s, available_qnty=%s, image=%s
            WHERE book_id=%s
            """
            values = (
                data['title'], data['author'], data.get('genre', ''),
                data.get('publisher', ''), data['year_publish'],
                data['ISBN'], data['available_qnty'], image_filename, data['book_id']
            )
        else:
            query = """
            UPDATE book 
            SET title=%s, author=%s, genre=%s, publisher=%s, 
                year_publish=%s, ISBN=%s, available_qnty=%s
            WHERE book_id=%s
            """
            values = (
                data['title'], data['author'], data.get('genre', ''),
                data.get('publisher', ''), data['year_publish'],
                data['ISBN'], data['available_qnty'], data['book_id']
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
    search_query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search_query:
        query = """
        SELECT * FROM reader
        WHERE name LIKE %s OR contact_number LIKE %s OR reference_id LIKE %s
        """
        cursor.execute(query, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        query = "SELECT * FROM reader"
        cursor.execute(query)

    readers = cursor.fetchall()
    cursor.close()

    return render_template('reader.html', readers=readers)

@app.route('/readers')
def manage_readers():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM reader")
    readers = cursor.fetchall()
    cursor.close()
    return render_template('reader.html', readers=readers)


@app.route('/add_reader', methods=['POST'])
def add_reader():
    try:
        name = request.form['name']
        contact_number = request.form['contact_number']
        reference_id = request.form['reference_id']
        address = request.form['address']
        email = request.form['email']

        cursor = mysql.connection.cursor()
        query = """
        INSERT INTO reader (name, contact_number, reference_id, address, email)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (name, contact_number, reference_id, address, email))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "Reader added successfully!"})

    except Exception as e:
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
        # Error handling
        return jsonify({"error": str(e)}), 500


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
            # Search for readers by name or ID
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT reader_id, name, email, contact_number, status
                FROM reader
                WHERE name LIKE %s OR reader_id LIKE %s
            """, (f"%{query}%", f"%{query}%"))
            readers = cursor.fetchall()
            cursor.close()

            # Return a properly formatted JSON response
            reader_data = []
            for reader in readers:
                reader_data.append({
                    'reader_id': reader[0],
                    'name': reader[1],
                    'email': reader[2],
                    'contact_number': reader[3],
                    'status': reader[4]
                })

            return jsonify(reader_data)
        except Exception as e:
            # Log the exception for debugging purposes
            print(f"Error during reader search: {e}")
            return jsonify({'error': 'An error occurred while fetching reader data'}), 500
    return jsonify([])  # Return an empty list if no query is provided


@app.route('/fetch_books', methods=['GET'])
def fetch_books():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT book_id, title, genre, author
        FROM book
        WHERE available_qnty > 0
    """)
    books = cursor.fetchall()
    cursor.close()

    return jsonify(books)


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

import uuid


@app.route('/issue_books', methods=['POST'])
def issue_books():
    data = request.json
    reader_id = data.get('reader_id')
    books = data.get('books')
    start_date = data.get('start_date')
    return_date = data.get('return_date')
    admin_id = data.get('admin_id')  # 🔹 Capture admin ID from request

    cur = mysql.connection.cursor()

    # 🔹 Generate a short transaction ID (you can use a timestamp for simplicity)
    import time
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

        # Reduce book quantity
        cur.execute("UPDATE book SET available_qnty = available_qnty - 1 WHERE book_id = %s AND available_qnty > 0",
                    (book_id,))

        # Increment the lend_book field for the reader
        cur.execute("UPDATE reader SET lend_book = lend_book + 1 WHERE reader_id = %s", (reader_id,))

    # Check if the updated lend_book count is greater than or equal to 5
    cur.execute("SELECT lend_book FROM reader WHERE reader_id = %s", (reader_id,))
    lend_book_count = cur.fetchone()[0]  # Get the updated lend_book count

    if lend_book_count >= 5:
        # If the reader has borrowed 5 or more books, set status to 'inactive'
        cur.execute("UPDATE reader SET status = 'inactive' WHERE reader_id = %s", (reader_id,))
        mysql.connection.commit()
        print(f"Reader ID {reader_id} status updated to inactive")


    # 🔹 Fetch admin name for the receipt
    cur.execute("SELECT name FROM admin WHERE admin_id = %s", (admin_id,))
    admin_name = cur.fetchone()
    admin_name = admin_name[0] if admin_name else "Unknown"

    # 🔹 Fetch reader name and contact details
    cur.execute("SELECT name, contact_number FROM reader WHERE reader_id = %s", (reader_id,))
    reader_data = cur.fetchone()
    reader_name = reader_data[0] if reader_data else "Unknown"
    reader_contact = reader_data[1] if reader_data else "Unknown"

    mysql.connection.commit()
    cur.close()

    ## existing code ...
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
        "books": [{"title": title} for title in book_titles]
    }

    # Debugging session data before returning it
    print(session['receipt_data'])

    return jsonify({
        "receipt_url": "/receipt",  # Optional: You can redirect the user to this URL after issuing books
        "receipt": session['receipt_data']  # Send the receipt as part of the response
    })
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


@app.route('/fetch_issued', methods=['GET'])
def fetch_issued():
    search_query = request.args.get('search', '')
    cur = mysql.connection.cursor()

    query = """
    SELECT issued.issued_number, issued.reader_id, reader.name, issued.book_id, 
           book.title, issued.start_date, issued.return_date, issued.transaction_id
    FROM issued
    JOIN reader ON issued.reader_id = reader.reader_id
    JOIN book ON issued.book_id = book.book_id
    WHERE reader.name LIKE %s OR issued.reader_id LIKE %s
    ORDER BY issued.issued_number DESC
    """
    cur.execute(query, (f"%{search_query}%", f"%{search_query}%"))
    issued_books = cur.fetchall()
    cur.close()

    # Convert tuples to list of dictionaries
    issued_books_list = [
        {
            "issued_number": row[0],
            "reader_id": row[1],
            "name": row[2],
            "book_id": row[3],
            "title": row[4],
            "start_date": row[5].strftime('%Y-%m-%d'),
            "return_date": row[6].strftime('%Y-%m-%d'),
            "transaction_id": row[7]
        }
        for row in issued_books
    ]

    return jsonify(issued_books_list)


@app.route('/list_issued')
def list_issued():
    return render_template('list_issued.html')


@app.route('/return')
def return_books():
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
    WHERE r.name LIKE %s OR r.reader_id LIKE %s;
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


from datetime import datetime
import time  # Import the time module

@app.route('/process_return', methods=['POST'])
def process_return():
    try:
        data = request.get_json()
        issued_number = data.get('issued_number')
        cur = mysql.connection.cursor()

        # Fetch issued book details
        cur.execute("SELECT reader_id, book_id, return_date FROM issued WHERE issued_number = %s", (issued_number,))
        issued_data = cur.fetchone()

        if not issued_data:
            return jsonify({'message': 'Issued record not found'}), 404

        reader_id, book_id, return_date = issued_data

        # Ensure return_date is today's date when returned
        today_date = datetime.today().date()  # Use the correct method to get today's date

        # Calculate exceed days (if any)
        if isinstance(return_date, str):
            return_date = datetime.strptime(return_date, '%Y-%m-%d').date()

        exceed_days = max(0, (today_date - return_date).days)
        fine = exceed_days * 50

        # Insert into return_book table, with today's date as return_date
        cur.execute(""" 
            INSERT INTO return_book (reader_id, book_id, issued_number, return_date, exceed_days, fine) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (reader_id, book_id, issued_number, today_date, exceed_days, fine))

        # Remove from issued table
        cur.execute("DELETE FROM issued WHERE issued_number = %s", (issued_number,))

        # Commit changes to the database
        mysql.connection.commit()

        # Fetch reader and book details for the receipt
        cur.execute("SELECT name FROM reader WHERE reader_id = %s", (reader_id,))
        reader_data = cur.fetchone()
        reader_name = reader_data[0] if reader_data else "Unknown"

        cur.execute("SELECT title FROM book WHERE book_id = %s", (book_id,))
        book_data = cur.fetchone()
        book_title = book_data[0] if book_data else "Unknown"
        # Update the available quantity in the book table
        cur.execute("UPDATE book SET available_qnty = available_qnty + 1 WHERE book_id = %s", (book_id,))

        # Update the lend_book count in the reader table
        cur.execute("UPDATE reader SET lend_book = lend_book - 1 WHERE reader_id = %s", (reader_id,))

        # Generate receipt data
        receipt_data = {
            "transaction_id": str(int(time.time())),  # Use time.time() from the time module for unique ID
            "reader": {
                "id": reader_id,
                "name": reader_name,
            },
            "book": {
                "title": book_title,
                "issued_number": issued_number
            },
            "return_date": today_date,
            "exceed_days": exceed_days,
            "fine": fine
        }

        # Return a response with receipt data
        return jsonify({
            'message': 'Book returned successfully',
            'receipt': receipt_data
        })

    except Exception as e:
        # Rollback in case of an error
        mysql.connection.rollback()

        print(f"Error occurred: {str(e)}")  # Log the error

        return jsonify({'error': 'An error occurred while processing the return. Please try again.'}), 500

if __name__ == '__main__':
    app.run(debug=True)