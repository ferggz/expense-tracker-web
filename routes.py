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

from functools import wraps
from datetime import datetime
from database import get_db_connection


bp = Blueprint("routes", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return view(*args, **kwargs)

    return wrapped_view


def get_filtered_expenses(connection, user_id, category, search):

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY date DESC, id DESC"

    return connection.execute(query, params).fetchall()


def get_total_amount(connection, user_id, category, search):

    query = """
        SELECT SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
    """

    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")

    return connection.execute(query, params).fetchone()


def calculate_dashboard_stats(expenses, total):

    expense_count = len(expenses)

    average = 0

    if expense_count > 0:
        average = total["total"] / expense_count

    category_totals = {}
    category_percentages = {}

    for expense in expenses:

        category_name = expense["category"]

        if category_name not in category_totals:
            category_totals[category_name] = 0

        category_totals[category_name] += expense["amount"]

    top_category = None
    top_amount = 0

    for category_name, amount in category_totals.items():

        if amount > top_amount:
            top_amount = amount
            top_category = category_name

    latest_expense = None

    if expenses:
        latest_expense = expenses[0]

    highest_expense = None

    if expenses:
        highest_expense = max(
            expenses,
            key=lambda expense: expense["amount"]
        )

    if total["total"]:

        for category_name, amount in category_totals.items():

            percentage = (amount / total["total"]) * 100

            category_percentages[category_name] = percentage

    return {
        "expense_count": expense_count,
        "average": average,
        "category_totals": category_totals,
        "category_percentages": category_percentages,
        "top_category": top_category,
        "top_amount": top_amount,
        "latest_expense": latest_expense,
        "highest_expense": highest_expense
    }


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
    
    if len(username) > 30:
        flash("Username too long", "error")
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

        created_at = datetime.now().strftime("%Y-%m-%d")

        connection.execute("""
            INSERT INTO users (username, password, created_at)
            VALUES (?, ?, ?)
        """, (username, password, created_at))

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

    user = connection.execute("""
        SELECT * FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    expenses = get_filtered_expenses(
        connection,
        session["user_id"],
        category,
        search
    )

    total = get_total_amount(
        connection,
        session["user_id"],
        category,
        search
    )

    stats = calculate_dashboard_stats(expenses, total)

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
        expense_count=stats["expense_count"],
        average=stats["average"],
        category_totals=stats["category_totals"],
        category_percentages=stats["category_percentages"],
        top_category=stats["top_category"],
        top_amount=stats["top_amount"],
        latest_expense=stats["latest_expense"],
        highest_expense=stats["highest_expense"],
        user=user
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
        
        if len(category) > 30:
            flash("Category too long", "error")
            return redirect("/add")

        if len(description) > 100:
            flash("Description too long", "error")
            return redirect("/add")
        
        date = request.form["date"]

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date", "error")
            return redirect("/add")

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
        
        if len(category) > 30:
            flash("Category too long", "error")
            return redirect(f"/edit/{expense_id}")

        if len(description) > 100:
            flash("Description too long", "error")
            return redirect(f"/edit/{expense_id}")
        
        category = request.form["category"].strip().title()
        description = request.form["description"].strip().title()
        date = request.form["date"]

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date", "error")
            return redirect(f"/edit/{expense_id}")

        if not category or not description:
            flash("Category and description cannot be empty", "error")
            return redirect(f"/edit/{expense_id}")

        connection.execute("""
            UPDATE expenses
            SET amount = ?, category = ?, description = ?, date = ?
            WHERE id = ? AND user_id = ?
        """, (amount, category, description, date, expense_id, session["user_id"]))

        connection.commit()
        connection.close()

        flash("Expense updated successfully", "success")

        return redirect("/dashboard")

    connection.close()

    return render_template("edit_expense.html", expense=expense)