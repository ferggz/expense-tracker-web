from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime
from functools import wraps

from database import get_db_connection


bp = Blueprint("routes", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return view(*args, **kwargs)

    return wrapped_view


@bp.route("/")
def home():
    return render_template("index.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = generate_password_hash(request.form["password"])
    
    if not username:
        flash("Username cannot be empty", "error")
        return redirect("/register")

        connection = get_db_connection()

        existing_user = connection.execute("""
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(?)
        """, (username,)).fetchone()

        if existing_user:
            connection.close()

            flash("Username already exists", "error")

            return redirect("/register")

        connection.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
        """, (username, password))

        connection.commit()
        connection.close()

        return redirect("/")

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute("""
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(?)
        """, (username,)).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/dashboard")

        flash("Invalid username or password", "error")
        return redirect("/login")

    return render_template("login.html")


@bp.route("/dashboard")
@login_required
def dashboard():

    category = request.args.get("category")
    sort = request.args.get("sort")
    search = request.args.get("search")

    connection = get_db_connection()

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [session["user_id"]]

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY date DESC, id DESC"

    expenses = connection.execute(query, params).fetchall()

    total_query = """
        SELECT SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
    """

    total_params = [session["user_id"]]

    if category:
        total_query += " AND category = ?"
        total_params.append(category)

    if search:
        total_query += " AND description LIKE ?"
        total_params.append(f"%{search}%")

    total = connection.execute(total_query, total_params).fetchone()
    expense_count = len(expenses)

    average = 0

    category_totals = {}
    category_percentages = {}

    if expense_count > 0:
        average = total["total"] / expense_count

    for expense in expenses:
        category_name = expense["category"]

        if category_name not in category_totals:
            category_totals[category_name] = 0

        category_totals[category_name] += expense["amount"]

    if total["total"]:

        for category_name, amount in category_totals.items():

            percentage = (amount / total["total"]) * 100

            category_percentages[category_name] = percentage

    if sort == "amount":
        expenses = sorted(
            expenses,
            key=lambda expense: expense["amount"],
            reverse=True
        )

    elif sort == "date":
        expenses = sorted(
            expenses,
            key=lambda expense: expense["date"],
            reverse=True
        )

    connection.close()

    return render_template(
        "dashboard.html",
        expenses=expenses,
        total=total["total"],
        category=category,
        sort=sort,
        search=search,
        expense_count=expense_count,
        average=average,
        category_totals=category_totals,
        category_percentages=category_percentages
    )


@bp.route("/logout")
@login_required
def logout():
    session.clear()

    return redirect("/login")


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("Invalid amount", "error")
            return redirect("/add")

        if amount <= 0:
            flash("Amount must be greater than 0", "error")
            return redirect("/add")
        
        category = request.form["category"].strip().title()
        description = request.form["description"].strip().title()

        if not category or not description:
            flash("Category and description cannot be empty", "error")
            return redirect("/add")
        
        date = datetime.now().strftime("%Y-%m-%d")

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO expenses (amount, category, description, date, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (amount, category, description, date, session["user_id"]))

        connection.commit()
        connection.close()

        flash("Expense added successfully", "success")

        return redirect("/dashboard")

    return render_template("add_expense.html")


@bp.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, session["user_id"]))

    connection.commit()
    connection.close()

    flash("Expense deleted successfully", "success")

    return redirect("/dashboard")


@bp.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):

    connection = get_db_connection()

    expense = connection.execute("""
        SELECT * FROM expenses
        WHERE id = ? AND user_id = ?
    """, (expense_id, session["user_id"])).fetchone()

    if expense is None:
        connection.close()
        flash("Expense not found", "error")

        return redirect("/dashboard")

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("Invalid amount")
            return redirect(f"/edit/{expense_id}")

        if amount <= 0:
            flash("Amount must be greater than 0")
            return redirect(f"/edit/{expense_id}")
        
        category = request.form["category"].strip().title()
        description = request.form["description"].strip().title()

        if not category or not description:
            flash("Category and description cannot be empty", "error")
            return redirect(f"/edit/{expense_id}")

        connection.execute("""
            UPDATE expenses
            SET amount = ?, category = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (amount, category, description, expense_id, session["user_id"]))

        connection.commit()
        connection.close()

        flash("Expense updated successfully", "success")

        return redirect("/dashboard")

    connection.close()

    return render_template("edit_expense.html", expense=expense)