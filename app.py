from flask import Flask, render_template, request, redirect, url_for


import mysql.connector

import decimal


image_folder = r"Photos"

app = Flask(__name__)

# Database Configuration
DB_HOST = "localhost"
DB_USER = "admin"
DB_PASSWORD = "MySql.Admin"
DB_NAME = "g6cafe"

# Create a connection to the database
def connect_db():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )


        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

def load_menu():
    connection = connect_db()
    if not connection:
        return {}

    cursor = connection.cursor()

    menu = {}

    try:
        # Fetch distinct category names from the correct column (category_name)
        cursor.execute("SELECT DISTINCT category_name FROM menu_details")
        categoryRows = cursor.fetchall()

        for categoryRow in categoryRows:
            # Assign category_name to catSTR
            catSTR = str(categoryRow[0])
            menu[catSTR] = []

            # Fetch items in each category using category_name
            cursor.execute("SELECT item_name, unit_price, photo FROM menu_details WHERE category_name = %s", (catSTR,))
            rows = cursor.fetchall()

            for row in rows:
                item_name, unit_price, photo = row
                menu[catSTR].append({"name": str(item_name), "price": decimal.Decimal(unit_price), "image": str(photo)})

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    cursor.close()
    connection.close()
    return menu

menu = load_menu()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def show_menu():
    return render_template('menu.html', menu=menu)

@app.route('/order', methods=['POST'])
def place_order():
    item_names = request.form.getlist('item')
    order = []
    total = 0

    for category, items in menu.items():
        for item in items:
            if item['name'] in item_names:
                order.append(item)
                total += item['price']

    # Calculate other amounts
    vat_amount = total * 0.12  # Example VAT calculation
    discount_amount = 0.00     # Assuming no discount for simplicity
    net_amount = total + vat_amount - discount_amount
    tender_amount = net_amount # Assuming exact payment for simplicity
    change_amount = tender_amount - net_amount

    # Insert into orders table
    connection = connect_db()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO orders (subtotal, vat_amount, discount_amount, net_amount, tender_amount, change_amount, receipt_number) "
            "VALUES (%s, %s, %s, %s, %s, %s, UUID())",
            (total, vat_amount, discount_amount, net_amount, tender_amount, change_amount)
        )
        order_id = cursor.lastrowid

        # Insert into order_details table
        for item in order:
            cursor.execute(
                "SELECT item_id FROM menu_details WHERE item_name = %s",
                (item['name'],)
            )
            item_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO order_details (order_id, item_id, quantity, subtotal) "
                "VALUES (%s, %s, %s, %s)",
                (order_id, item_id, 1, item['price'])  # Assuming quantity is 1 for simplicity
            )

        connection.commit()
        message = "Order placed successfully!"

    except mysql.connector.Error as err:
        connection.rollback()
        message = f"Error: {err}"

    cursor.close()
    connection.close()

    return render_template('order.html', order=order, total=total, message=message)



if __name__ == "__main__":
    app.run(debug=True)