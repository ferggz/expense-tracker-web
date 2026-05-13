from flask import Flask
from routes import bp
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(bp)


if __name__ == "__main__":
    app.run(debug=True)