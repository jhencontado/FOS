from flask import Flask, render_template, request, jsonify
from models import db, Book  # Import database models

app = Flask(__name__)

# Route to serve book.html
@app.route("/book")
def manage_books():
    return render_template("book.html")

# Fetch all books
@app.route("/get_books", methods=["GET"])
def get_books():
    books = Book.query.all()
    books_list = [{"id": b.id, "title": b.title, "author": b.author, "year": b.year} for b in books]
    return jsonify(books_list)

# Add a book
@app.route("/add_book", methods=["POST"])
def add_book():
    data = request.form
    new_book = Book(title=data["title"], author=data["author"], year=data["year"])
    db.session.add(new_book)
    db.session.commit()
    return jsonify({"message": "Book added successfully!"})

# Delete a book
@app.route("/delete_book/<int:id>", methods=["DELETE"])
def delete_book(id):
    book = Book.query.get(id)
    if book:
        db.session.delete(book)
        db.session.commit()
        return jsonify({"message": "Book deleted successfully!"})
    return jsonify({"error": "Book not found!"})

# Update a book
@app.route("/update_book/<int:id>", methods=["PUT"])
def update_book(id):
    data = request.json
    book = Book.query.get(id)
    if book:
        book.title = data["title"]
        book.author = data["author"]
        book.year = data["year"]
        db.session.commit()
        return jsonify({"message": "Book updated successfully!"})
    return jsonify({"error": "Book not found!"})

if __name__ == "__main__":
    app.run(debug=True)
