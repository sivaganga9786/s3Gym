from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import os
import cloudinary
import cloudinary.uploader
from sqlalchemy import text  # for one-time column addition
from sqlalchemy import extract, func
from flask import request
# Flask config
# Flask config
import urllib.parse

app = Flask(__name__)

# Ensure proper PostgreSQL URI handling
db_url = os.getenv("DATABASE_URL", "sqlite:///clients.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")
if "sslmode=" not in db_url and "sqlite" not in db_url:
    db_url += "?sslmode=require"

app.config.update(
    SQLALCHEMY_DATABASE_URI=db_url,
    SECRET_KEY=os.getenv('SECRET_KEY', 'siva-secret'),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)

# Fix for Neon idle disconnects
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280  # optional: helps against Neon timeout
}


# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

db = SQLAlchemy(app)

# Helpers
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# DB Model
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
    profile_image = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True)  # ✅ Soft delete flag
@app.route('/financial_summary')
def financial_summary():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    selected_month = int(request.args.get("month", datetime.now().month))
    selected_year = int(request.args.get("year", datetime.now().year))

    # Filter paid clients only for the selected month/year
    clients = Client.query.filter(
        Client.payment_status == 'paid',
        db.extract('month', Client.join_date) == selected_month,
        db.extract('year', Client.join_date) == selected_year
    ).all()

    student_total = sum(c.fees for c in clients if c.client_type == "student")
    general_total = sum(c.fees for c in clients if c.client_type == "general")
    total_revenue = student_total + general_total

    return render_template("financial_summary.html",
        student_total=student_total,
        general_total=general_total,
        total_revenue=total_revenue,
        selected_month=selected_month,
        selected_year=selected_year,
        current_year=datetime.now().year
    )

# Routes
@app.route('/')
def root():
    return redirect(url_for('home'))
@app.route('/check_phone/<phone_number>')
def check_phone(phone_number):
    existing_client = Client.query.filter_by(phone=phone_number).first()
    return jsonify({'exists': existing_client is not None})


@app.route('/home')
def home():
    if session.get('admin_logged_in'):
        today = datetime.today().date()
        next_3_days = today + timedelta(days=3)

        total_clients = Client.query.filter_by(is_active=True).count()
        total_students = Client.query.filter_by(client_type='student', is_active=True).count()
        total_general = Client.query.filter_by(client_type='general', is_active=True).count()
        due_clients_count = Client.query.filter(
            Client.payment_status == 'unpaid',
            Client.payment_due_date <= next_3_days,
            Client.is_active == True
        ).count()
    else:
        total_clients = total_students = total_general = due_clients_count = 0

    return render_template('home.html',
        current_year=datetime.now().year,
        total_clients=total_clients,
        total_students=total_students,
        total_general=total_general,
        due_clients_count=due_clients_count
    )

@app.route('/download_financial_excel')
def download_financial_excel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    month = int(request.args.get('month'))
    year = int(request.args.get('year'))

    students = Client.query.filter(
        Client.client_type == 'student',
        Client.payment_status == 'paid',
        extract('month', Client.join_date) == month,
        extract('year', Client.join_date) == year
    ).all()

    general = Client.query.filter(
        Client.client_type == 'general',
        Client.payment_status == 'paid',
        extract('month', Client.join_date) == month,
        extract('year', Client.join_date) == year
    ).all()

    # Prepare Excel content
    data = []
    for c in students + general:
        data.append({
            'Name': c.name,
            'Contact': c.contact,
            'Type': c.client_type,
            'Fees': c.fees,
            'Join Date': c.join_date,
            'Status': c.payment_status
        })

    df = pd.DataFrame(data)

    # Add summary row
    total_fees = df['Fees'].sum()
    df.loc[len(df)] = ['TOTAL', '', '', total_fees, '', '']

    os.makedirs('static/reports', exist_ok=True)
    filename = f'static/reports/Financial_{month}_{year}.xlsx'
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Securely pull from Render environment
        admin_user = os.environ["ADMIN_USERNAME"]
        admin_pass = os.environ["ADMIN_PASSWORD"]

        if username == admin_user and password == admin_pass:
            session['admin_logged_in'] = True
            return redirect(url_for('home'))

        flash("Invalid credentials", 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out", 'info')
    return redirect(url_for('home'))

@app.route('/index')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    category = request.args.get('category')
    query = request.args.get('search', '')
    base_query = Client.query.filter(Client.payment_status == 'paid', Client.is_active == True)

    if category == 'student':
        base_query = base_query.filter(Client.client_type == 'student')
    elif category == 'general':
        base_query = base_query.filter(Client.client_type == 'general')

    if query:
        base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

    clients = base_query.all()
    return render_template('paid_clients.html', clients=clients, query=query, category=category)

@app.route('/due')
def due_clients():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    today = datetime.today().date()
    next_3_days = today + timedelta(days=3)

    due_soon = Client.query.filter(
        Client.payment_status == 'paid',
        Client.payment_due_date <= next_3_days,
        Client.is_active == True
    ).all()

    for client in due_soon:
        client.payment_status = 'unpaid'
        client.last_updated = datetime.now()
    db.session.commit()

    due_clients = Client.query.filter(
        Client.payment_status == 'unpaid',
        Client.payment_due_date <= next_3_days,
        Client.is_active == True
    ).all()

    return render_template('due_clients.html', clients=due_clients)

@app.route('/mark_paid/<int:client_id>', methods=['POST'])
def mark_paid(client_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    client = Client.query.get_or_404(client_id)
    client.payment_status = 'paid'
    client.payment_due_date = datetime.today().date() + timedelta(days=30)
    client.last_updated = datetime.now()
    db.session.commit()
    flash(f"{client.name} marked as paid.", "success")
    return redirect(url_for('due_clients'))

@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            name = request.form['name']
            contact = request.form['contact']
            gender = request.form['gender']
            client_type = request.form['client_type']
            join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
            payment_status = request.form['payment_status']
            goal = request.form.get('goal')
            weight = float(request.form['weight']) if request.form.get('weight') else None
            fees = int(request.form['fees']) if request.form.get('fees') else 0
            due = join_date + timedelta(days=30)

            if not all([name, contact, gender, client_type, join_date, payment_status]):
                flash("All required fields must be filled.", 'danger')
                return redirect(url_for('add_client'))

            if not contact.isdigit() or len(contact) != 10:
                flash("Contact must be 10 digits.", 'danger')
                return redirect(url_for('add_client'))

            if weight and (weight < 50 or weight > 110):
                flash("Weight must be between 50–110kg.", 'danger')
                return redirect(url_for('add_client'))

            image_url = None
            file = request.files.get('profile_image')
            if file and allowed_file(file.filename):
                upload_result = cloudinary.uploader.upload(file)
                image_url = upload_result.get("secure_url")

            client = Client(
                name=name, contact=contact, goal=goal, weight=weight,
                gender=gender, client_type=client_type, fees=fees,
                payment_status=payment_status, join_date=join_date,
                payment_due_date=due, profile_image=image_url,
                last_updated=datetime.now(), is_active=True
            )
            db.session.add(client)
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
                upload_result = cloudinary.uploader.upload(file)
                client.profile_image = upload_result.get("secure_url")

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

    client = Client.query.get_or_404(client_id)
    client.is_active = False  # ✅ Soft delete
    client.last_updated = datetime.now()
    db.session.commit()
    flash("Client deleted (soft delete).", 'info')
    return redirect(url_for('index'))

@app.route('/master')
def master_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    clients = Client.query.order_by(Client.join_date.desc()).all()  # Show all
    return render_template('master_list.html', clients=clients)

@app.route('/download_excel_master')
def download_excel_master():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    clients = Client.query.filter_by(payment_status='paid').order_by(Client.join_date.desc()).all()
    df = pd.DataFrame([{
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
    } for c in clients])

    os.makedirs('static/backups', exist_ok=True)
    path = 'static/backups/master_clients.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route('/download_excel/<client_type>')
def download_excel_by_type(client_type):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if client_type not in ['student', 'general']:
        flash("Invalid client type!", 'danger')
        return redirect(url_for('index'))

    clients = Client.query.filter_by(client_type=client_type, is_active=True).all()
    df = pd.DataFrame([{
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
    } for c in clients])

    os.makedirs('static/backups', exist_ok=True)
    path = f'static/backups/{client_type}_clients.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route('/download_due_excel')
def download_due_excel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    today = datetime.today().date()
    next_3_days = today + timedelta(days=3)

    due_clients = Client.query.filter(
        Client.payment_status == 'unpaid',
        Client.payment_due_date <= next_3_days
    ).all()

    data = []
    for c in due_clients:
        data.append({
            'Name': c.name,
            'Contact': c.contact,
            'Type': c.client_type,
            'Join Date': c.join_date,
            'Due Date': c.payment_due_date,
            'Status': c.payment_status
        })

    df = pd.DataFrame(data)
    df.loc[len(df)] = ['TOTAL', '', '', '', '', f'{len(due_clients)} Clients']

    os.makedirs('static/reports', exist_ok=True)
    path = f'static/reports/Due_Clients_{today}.xlsx'
    df.to_excel(path, index=False)

    return send_file(path, as_attachment=True)

# App entry
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        try:
            db.session.execute(text("ALTER TABLE client ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            db.session.commit()
            print("✅ 'is_active' column added.")
        except Exception as e:
            print("⚠️ Skipping column creation (may already exist):", e)
    app.run(host='0.0.0.0', port=10000)



