import datetime

import bcrypt
from flask import Flask, render_template,jsonify, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL

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
today_date = datetime.date.today()
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor for dictionary results

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
    cursor.close()
    # ✅ Debugging: I-print ang books sa terminal para makita kung nakuha ito nang tama
    print("Fetched books:", books)
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(books=books)

    return render_template('book.html', books=books, search_query=search_query)


# 📌 Route: Display Readers
@app.route('/readers', methods=['GET'])
def readers():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM reader")
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
         # ✅ Check if form fields exist before accessing them
        if not all(key in request.form for key in ['name', 'contact_number', 'reference_id', 'address', 'email']):
         return "Error: Missing required form fields", 400

        name = request.form['name']
        contact_number = request.form['contact_number']
        reference_id = request.form['reference_id']  # 🔥 Ensure this exists in the form
        address = request.form['address']
        email = request.form['email']

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO reader (name, contact_number, reference_id, address, email) VALUES (%s, %s, %s, %s, %s)",
            (name, contact_number, reference_id, address, email)
        )
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('manage_readers'))



@app.route('/delete_reader/<int:reader_id>', methods=['POST'])
def delete_reader(reader_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM reader WHERE reader_id = %s", (reader_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('manage_readers'))


@app.route('/update_reader', methods=['POST'])
def update_reader():
    reader_id = request.form['reader_id']
    name = request.form['name']
    contact_number = request.form['contact_number']
    reference_id = request.form['reference_id']
    address = request.form['address']
    email = request.form['email']

    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE reader SET name=%s, contact_number=%s, reference_id=%s, address=%s, email=%s WHERE reader_id=%s",
        (name, contact_number, reference_id, address, email, reader_id)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('manage_readers'))


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

    if not query:
        return jsonify([])

    cur = mysql.connection.cursor()
    search_query = f"""
        SELECT reader_id, name, email, contact_number, status 
        FROM reader 
        WHERE name LIKE %s OR reader_id LIKE %s
    """
    like_query = f"%{query}%"
    cur.execute(search_query, (like_query, like_query))
    results = cur.fetchall()
    cur.close()

    return jsonify(results)


@app.route('/fetch_books', methods=['GET'])
def fetch_books():
    cur = mysql.connection.cursor()
    cur.execute("SELECT book_id, title FROM book")
    books = cur.fetchall()
    cur.close()
    return jsonify(books)


import uuid

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

    # 🔹 Generate a unique transaction ID
    transaction_id = str(uuid.uuid4())

    issued_numbers = []

    for book_id in books:
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

    # Count books currently borrowed by the reader
    cur.execute("SELECT COUNT(*) FROM issued WHERE reader_id = %s AND return_date IS NULL", (reader_id,))
    issued_count = cur.fetchone()[0]

    print(f"Reader ID: {reader_id}, Issued Books: {issued_count}")

    # If the reader has borrowed 5 or more books, set status to 'inactive'
    if issued_count >= 5:
        cur.execute("UPDATE reader SET status = 'inactive' WHERE reader_id = %s", (reader_id,))
        mysql.connection.commit()
        print("Status updated to inactive")

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

    return jsonify({
        "receipt_url": "/receipt",
        "receipt": {
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
            "books": books
        }
    })


@app.route('/receipt', methods=['GET'])
def receipt():
    return render_template('receipt.html')  # Ensure this file exists in /templates

@app.route('/get_logged_in_admin', methods=['GET'])
def get_logged_in_admin():
    if 'loggedin' in session:
        return jsonify({
            "admin_id": session['admin_id'],
            "admin_name": session['admin_name']
        })
    return jsonify({"error": "Not logged in"}), 401


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

        # Ensure return_date is a valid date object
        if isinstance(return_date, str):
            return_date = datetime.strptime(return_date, '%Y-%m-%d').date()

        exceed_days = max(0, (datetime.date.today() - return_date).days)
        fine = exceed_days * 50

        # Insert into return_book table, keeping the original return_date from issued table
        cur.execute("""
            INSERT INTO return_book (reader_id, book_id, issued_number, return_date, exceed_days, fine, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (reader_id, book_id, issued_number, return_date, exceed_days, fine))

        # Remove from issued table
        cur.execute("DELETE FROM issued WHERE issued_number = %s", (issued_number,))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Book returned successfully'})

    except Exception as e:
        mysql.connection.rollback()  # Rollback in case of error
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)