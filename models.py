import MySQLdb

db = MySQLdb.connect("localhost", "dbadmin", "Jheyan061709", "library")
cursor = db.cursor()


from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)



cursor.execute('''CREATE TABLE IF NOT EXISTS reader (
    reader_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    reference_id VARCHAR(50) NOT NULL,
    address TEXT NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
    status status ENUM('active', 'inactive') DEFAULT 'active'
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS book (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    genre VARCHAR(100) NULL,
    publisher VARCHAR(255) NOT NULL,
    year_publish YEAR NOT NULL,
    ISBN VARCHAR(20) UNIQUE NOT NULL,
    image VARCHAR(20) null ,
    available_qnty INT NOT NULL
    DECIMAL(10,2) NOT NULL DEFAULT 0.00;
)''')

cursor.execute('''-''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role ENUM('Librarian', 'Manager', 'Staff') NOT NULL DEFAULT 'Staff'
)''')


cursor.execute('''CREATE TABLE return_book (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    reader_id INT NOT NULL,
    book_id INT NOT NULL,
    issued_number INT NOT NULL,
    return_date DATE NOT NULL,
    exceed_days INT DEFAULT 0,
    fine DECIMAL(10,2) DEFAULT 0.00,
    returned ENUM('no', 'yes') DEFAULT 'no',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (reader_id) REFERENCES reader(reader_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES book(book_id) ON DELETE CASCADE,
)''')


cursor.execute('''CREATE TABLE IF NOT EXISTS issued (
    issued_number INT AUTO_INCREMENT PRIMARY KEY,
    reader_id INT NOT NULL,
    book_id INT NOT NULL,
    start_date DATE NOT NULL,
    return_date DATE NOT NULL,
    transaction_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES reader(reader_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES book(book_id) ON DELETE CASCADE
    FOREIGN KEY (admin_id) REFERENCES admin(admin_id);
)''')



db.commit()
db.close()
