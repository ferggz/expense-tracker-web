from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "database.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
        """, (username, password))

        connection.commit()
        connection.close()

        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute("""
            SELECT * FROM users
            WHERE username = ? AND password = ?
        """, (username, password)).fetchone()

        connection.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    category = request.args.get("category")

    connection = get_db_connection()

    if category:
        expenses = connection.execute("""
            SELECT * FROM expenses
            WHERE user_id = ? AND category = ?
        """, (session["user_id"], category)).fetchall()

        total = connection.execute("""
            SELECT SUM(amount) AS total
            FROM expenses
            WHERE user_id = ? AND category = ?
        """, (session["user_id"], category)).fetchone()

    else:
        expenses = connection.execute("""
            SELECT * FROM expenses
            WHERE user_id = ?
        """, (session["user_id"],)).fetchall()

        total = connection.execute("""
            SELECT SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?
        """, (session["user_id"],)).fetchone()

    connection.close()

    return render_template(
        "dashboard.html",
        expenses=expenses,
        total=total["total"],
        category=category
    )


@app.route("/logout")
def logout():
    session.clear()

    return redirect("/login")


@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        amount = float(request.form["amount"])
        category = request.form["category"]
        description = request.form["description"]
        date = datetime.now().strftime("%Y-%m-%d")

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO expenses (amount, category, description, date, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (amount, category, description, date, session["user_id"]))

        connection.commit()
        connection.close()

        return redirect("/dashboard")

    return render_template("add_expense.html")


@app.route("/delete/<int:expense_id>")
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, session["user_id"]))

    connection.commit()
    connection.close()

    return redirect("/dashboard")


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()

    expense = connection.execute("""
        SELECT * FROM expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, session["user_id"])).fetchone()

    if expense is None:
        connection.close()
        return redirect("/dashboard")

    if request.method == "POST":
        amount = float(request.form["amount"])
        category = request.form["category"]
        description = request.form["description"]

        connection.execute("""
            UPDATE expenses
            SET amount = ?, category = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (amount, category, description, expense_id, session["user_id"]))

        connection.commit()
        connection.close()

        return redirect("/dashboard")

    connection.close()

    return render_template("edit_expense.html", expense=expense)


if __name__ == "__main__":
    app.run(debug=True)