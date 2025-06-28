from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
app.config['SECRET_KEY'] = 'siva-secret'
db = SQLAlchemy(app)

# ✅ Define the Client model
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    goal = db.Column(db.String(200))
    weight = db.Column(db.Float)
    payment_status = db.Column(db.String(20))
    last_updated = db.Column(db.DateTime)

# ✅ Route: Home - List all clients
@app.route('/')
def index():
    clients = Client.query.all()
    return render_template("clients.html", clients=clients)

# ✅ Route: Add new client
@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        goal = request.form['goal']
        weight = float(request.form['weight'])
        payment_status = request.form['payment_status']
        new_client = Client(
            name=name,
            contact=contact,
            goal=goal,
            weight=weight,
            payment_status=payment_status,
            last_updated=datetime.now()
        )
        db.session.add(new_client)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_client.html')

# ✅ Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure the DB is created before running
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
