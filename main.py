import os
from flask import Flask

# Create the Flask app
app = Flask(__name__)

# Configure the app
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Import routes (need to be imported after app is defined)
from app import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
