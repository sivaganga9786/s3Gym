from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
db = SQLAlchemy(app)

@app.route('/')
def index():
    return render_template("clients.html")

if __name__ == '__main__':
    app.run()
