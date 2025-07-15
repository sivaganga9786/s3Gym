from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from dotenv import load_dotenv
import pandas as pd
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///clients.db'),
    SECRET_KEY=os.getenv('SECRET_KEY', 'siva-secret'),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.lower().rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    goal = db.Column(db.String(200))
    weight = db.Column(db.Float)
    gender = db.Column(db.String(10))
    client_type = db.Column(db.String(20))
    fees = db.Column(db.Integer)
    payment_status = db.Column(db.String(20))
    join_date = db.Column(db.Date)
    payment_due_date = db.Column(db.Date)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    profile_image = db.Column(db.String(120), nullable=True)

@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html', current_year=datetime.now().year)

@app.route('/index')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    category = request.args.get('category')
    query = request.args.get('search', '')
    today = datetime.today().date()

    base_query = Client.query
    if category == 'student':
        base_query = base_query.filter(Client.client_type == 'student')
    elif category == 'general':
        base_query = base_query.filter(Client.client_type == 'general')

    if query:
        base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

    clients = base_query.all()

    upcoming_due = base_query.filter(
        Client.payment_status == 'unpaid',
        Client.payment_due_date >= today,
        Client.payment_due_date <= today + timedelta(days=2)
    ).all()

    return render_template('clients.html', clients=clients, upcoming_due=upcoming_due, query=query, category=category)

@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            contact = request.form.get('contact')
            gender = request.form.get('gender')
            client_type = request.form.get('client_type')
            join_date_str = request.form.get('join_date')
            payment_status = request.form.get('payment_status')

            if not all([name, contact, gender, client_type, join_date_str, payment_status]):
                flash("All required fields must be filled.", 'danger')
                return redirect(url_for('add_client'))

            if not contact.isdigit() or len(contact) != 10:
                flash("Contact number must be exactly 10 digits.", 'danger')
                return redirect(url_for('add_client'))

            join_date = datetime.strptime(join_date_str, "%Y-%m-%d").date()
            due = join_date + timedelta(days=30)

            goal = request.form.get('goal')
            weight_str = request.form.get('weight')
            weight = float(weight_str) if weight_str else None

            if weight and (weight < 50 or weight > 110):
                flash("Weight must be between 50–110 kg.", 'danger')
                return redirect(url_for('add_client'))

            fees_str = request.form.get('fees')
            fees = int(fees_str) if fees_str and fees_str.isdigit() else 0

            file = request.files.get('profile_image')
            fname = None
            if file and allowed_file(file.filename):
                fname = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

            c = Client(
                name=name,
                contact=contact,
                goal=goal,
                weight=weight,
                gender=gender,
                client_type=client_type,
                fees=fees,
                payment_status=payment_status,
                join_date=join_date,
                payment_due_date=due,
                profile_image=fname,
                last_updated=datetime.now()
            )
            db.session.add(c)
            db.session.commit()
            flash("Client added!", 'success')
            return redirect(url_for('index'))

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f"Error: {e}", 'danger')
            return redirect(url_for('add_client'))

    return render_template('add_client.html')

@app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        try:
            client.name = request.form['name']
            client.contact = request.form['contact']
            client.goal = request.form['goal']
            client.weight = float(request.form['weight']) if request.form.get('weight') else None
            client.gender = request.form['gender']
            client.client_type = request.form['client_type']
            client.fees = int(request.form['fees']) if request.form.get('fees') else 0
            client.payment_status = request.form['payment_status']
            client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
            client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

            file = request.files.get('profile_image')
            if file and allowed_file(file.filename):
                fname = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, fname))
                client.profile_image = fname

            client.last_updated = datetime.now()
            db.session.commit()
            flash("Client updated!", 'success')
            return redirect(url_for('index'))

        except Exception as e:
            flash(f"Error: {e}", 'danger')
            return redirect(url_for('edit_client', client_id=client_id))

    return render_template('edit_client.html', client=client)

@app.route('/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    db.session.delete(Client.query.get_or_404(client_id))
    db.session.commit()
    flash("Client deleted.", 'info')
    return redirect(url_for('index'))

@app.route('/due')
def due_clients():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    today = datetime.today().date()
    next_3_days = today + timedelta(days=3)

    due = Client.query.filter(
        or_(
            Client.payment_due_date < today,
            Client.payment_due_date <= next_3_days
        )
    ).all()
    return render_template('due_clients.html', clients=due)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('home'))
        flash("Invalid credentials", 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out", 'info')
    return redirect(url_for('home'))
@app.route('/download_excel/<client_type>')
def download_excel_by_type(client_type):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if client_type not in ['student', 'general']:
        flash("Invalid client type!", 'danger')
        return redirect(url_for('index'))

    clients = Client.query.filter_by(client_type=client_type).all()

    data = [{
        'Name': c.name,
        'Contact': c.contact,
        'Goal': c.goal,
        'Weight': c.weight,
        'Gender': c.gender,
        'Type': c.client_type,
        'Fees': c.fees,
        'Payment Status': c.payment_status,
        'Join Date': c.join_date,
        'Due Date': c.payment_due_date,
        'Last Updated': c.last_updated
    } for c in clients]

    import pandas as pd, os
    df = pd.DataFrame(data)
    os.makedirs('static/backups', exist_ok=True)
    path = f'static/backups/{client_type}_clients.xlsx'
    df.to_excel(path, index=False)

    return send_file(path, as_attachment=True)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=10000)
