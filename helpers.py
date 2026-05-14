from flask import session

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