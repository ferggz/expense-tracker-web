import sqlite3

connection = sqlite3.connect("database.db")

cursor = connection.cursor()

cursor.execute("""
INSERT INTO users (username, password)
VALUES (?, ?)
""", ("fer", "1234"))

connection.commit()
connection.close()

print("User added")