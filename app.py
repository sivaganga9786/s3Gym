from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import os
import cloudinary
import cloudinary.uploader

# Flask config
app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///clients.db'),
    SECRET_KEY=os.getenv('SECRET_KEY', 'siva-secret'),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024  # 5MB max upload
)

# Cloudinary credentials from environment variables
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

# Routes
@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    today = datetime.today().date()
    next_3_days = today + timedelta(days=3)

    total_clients = Client.query.count()
    total_students = Client.query.filter_by(client_type='student').count()
    total_general = Client.query.filter_by(client_type='general').count()
    due_clients_count = Client.query.filter(
        Client.payment_status == 'unpaid',
        Client.payment_due_date <= next_3_days
    ).count()

    return render_template('home.html',
        current_year=datetime.now().year,
        total_clients=total_clients,
        total_students=total_students,
        total_general=total_general,
        due_clients_count=due_clients_count
    )

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

@app.route('/index')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    category = request.args.get('category')
    query = request.args.get('search', '')
    base_query = Client.query.filter(Client.payment_status == 'paid')

    if category == 'student':
        base_query = base_query.filter(Client.client_type == 'student')
    elif category == 'general':
        base_query = base_query.filter(Client.client_type == 'general')

    if query:
        base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

    clients = base_query.all()
    return render_template('paid_clients.html', clients=clients, query=query, category=category)

@app.route('/paid')  # Optional: keep for backwards compatibility
def paid_clients():
    return redirect(url_for('index'))

@app.route('/due')
def due_clients():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    today = datetime.today().date()
    next_3_days = today + timedelta(days=3)

    due_soon = Client.query.filter(
        Client.payment_status == 'paid',
        Client.payment_due_date <= next_3_days
    ).all()

    for client in due_soon:
        client.payment_status = 'unpaid'
        client.last_updated = datetime.now()

    db.session.commit()

    due_clients = Client.query.filter(
        Client.payment_status == 'unpaid',
        Client.payment_due_date <= next_3_days
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
                last_updated=datetime.now()
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

    db.session.delete(Client.query.get_or_404(client_id))
    db.session.commit()
    flash("Client deleted.", 'info')
    return redirect(url_for('index'))

@app.route('/master')
def master_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    clients = Client.query.order_by(Client.join_date.desc()).all()
    return render_template('master_list.html', clients=clients)

@app.route('/download_excel_master')
def download_excel_master():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    clients = Client.query.order_by(Client.join_date.desc()).all()
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

    clients = Client.query.filter_by(client_type=client_type).all()
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

# App run
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=10000)




# from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# import pandas as pd
# import os

# app = Flask(__name__)
# app.config.update(
#     SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///clients.db'),
#     SECRET_KEY=os.getenv('SECRET_KEY', 'siva-secret'),
#     MAX_CONTENT_LENGTH=5 * 1024 * 1024
# )

# db = SQLAlchemy(app)

# UPLOAD_FOLDER = 'static/uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     gender = db.Column(db.String(10))
#     client_type = db.Column(db.String(20))
#     fees = db.Column(db.Integer)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date)
#     payment_due_date = db.Column(db.Date)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# @app.route('/')
# def root():
#     return redirect(url_for('home'))

# @app.route('/home')
# def home():
#     today = datetime.today().date()
#     next_3_days = today + timedelta(days=3)

#     total_clients = Client.query.count()
#     total_students = Client.query.filter_by(client_type='student').count()
#     total_general = Client.query.filter_by(client_type='general').count()
#     due_clients_count = Client.query.filter(
#         Client.payment_status == 'unpaid',
#         Client.payment_due_date <= next_3_days
#     ).count()

#     return render_template(
#         'home.html',
#         current_year=datetime.now().year,
#         total_clients=total_clients,
#         total_students=total_students,
#         total_general=total_general,
#         due_clients_count=due_clients_count
#     )

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash("Invalid credentials", 'danger')
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash("Logged out", 'info')
#     return redirect(url_for('home'))

# @app.route('/index')  # Paid Clients
# def index():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     category = request.args.get('category')
#     query = request.args.get('search', '')
#     base_query = Client.query.filter(Client.payment_status == 'paid')

#     if category == 'student':
#         base_query = base_query.filter(Client.client_type == 'student')
#     elif category == 'general':
#         base_query = base_query.filter(Client.client_type == 'general')

#     if query:
#         base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

#     clients = base_query.all()

#     return render_template('paid_clients.html', clients=clients, query=query, category=category)

# @app.route('/due')
# def due_clients():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     next_3_days = today + timedelta(days=3)

#     # Auto mark as unpaid if within due range
#     due_soon_clients = Client.query.filter(
#         Client.payment_status == 'paid',
#         Client.payment_due_date <= next_3_days
#     ).all()

#     for client in due_soon_clients:
#         client.payment_status = 'unpaid'
#         client.last_updated = datetime.now()

#     db.session.commit()

#     # Show unpaid clients
#     due_clients = Client.query.filter(
#         Client.payment_status == 'unpaid',
#         Client.payment_due_date <= next_3_days
#     ).all()

#     return render_template('due_clients.html', clients=due_clients)

# @app.route('/mark_paid/<int:client_id>', methods=['POST'])
# def mark_paid(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     client.payment_status = 'paid'
#     client.payment_due_date = datetime.today().date() + timedelta(days=30)
#     client.last_updated = datetime.now()
#     db.session.commit()
#     flash(f"{client.name} marked as paid.", "success")
#     return redirect(url_for('due_clients'))

# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         try:
#             name = request.form.get('name')
#             contact = request.form.get('contact')
#             gender = request.form.get('gender')
#             client_type = request.form.get('client_type')
#             join_date_str = request.form.get('join_date')
#             payment_status = request.form.get('payment_status')

#             if not all([name, contact, gender, client_type, join_date_str, payment_status]):
#                 flash("All required fields must be filled.", 'danger')
#                 return redirect(url_for('add_client'))

#             if not contact.isdigit() or len(contact) != 10:
#                 flash("Contact number must be exactly 10 digits.", 'danger')
#                 return redirect(url_for('add_client'))

#             join_date = datetime.strptime(join_date_str, "%Y-%m-%d").date()
#             due = join_date + timedelta(days=30)

#             goal = request.form.get('goal')
#             weight_str = request.form.get('weight')
#             weight = float(weight_str) if weight_str else None
#             if weight and (weight < 50 or weight > 110):
#                 flash("Weight must be between 50–110 kg.", 'danger')
#                 return redirect(url_for('add_client'))

#             fees_str = request.form.get('fees')
#             fees = int(fees_str) if fees_str and fees_str.isdigit() else 0

#             file = request.files.get('profile_image')
#             fname = None
#             if file and allowed_file(file.filename):
#                 fname = secure_filename(file.filename)
#                 file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

#             c = Client(
#                 name=name,
#                 contact=contact,
#                 goal=goal,
#                 weight=weight,
#                 gender=gender,
#                 client_type=client_type,
#                 fees=fees,
#                 payment_status=payment_status,
#                 join_date=join_date,
#                 payment_due_date=due,
#                 profile_image=fname,
#                 last_updated=datetime.now()
#             )
#             db.session.add(c)
#             db.session.commit()
#             flash("Client added!", 'success')
#             return redirect(url_for('index'))

#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             flash(f"Error: {e}", 'danger')
#             return redirect(url_for('add_client'))

#     return render_template('add_client.html')

# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)

#     if request.method == 'POST':
#         try:
#             client.name = request.form['name']
#             client.contact = request.form['contact']
#             client.goal = request.form['goal']
#             client.weight = float(request.form['weight']) if request.form.get('weight') else None
#             client.gender = request.form['gender']
#             client.client_type = request.form['client_type']
#             client.fees = int(request.form['fees']) if request.form.get('fees') else 0
#             client.payment_status = request.form['payment_status']
#             client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#             client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#             file = request.files.get('profile_image')
#             if file and allowed_file(file.filename):
#                 fname = secure_filename(file.filename)
#                 file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
#                 client.profile_image = fname

#             client.last_updated = datetime.now()
#             db.session.commit()
#             flash("Client updated!", 'success')
#             return redirect(url_for('index'))

#         except Exception as e:
#             flash(f"Error: {e}", 'danger')
#             return redirect(url_for('edit_client', client_id=client_id))

#     return render_template('edit_client.html', client=client)

# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     db.session.delete(Client.query.get_or_404(client_id))
#     db.session.commit()
#     flash("Client deleted.", 'info')
#     return redirect(url_for('index'))

# @app.route('/master')
# def master_list():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     clients = Client.query.order_by(Client.join_date.desc()).all()
#     return render_template('master_list.html', clients=clients)

# @app.route('/download_excel_master')
# def download_excel_master():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     clients = Client.query.order_by(Client.join_date.desc()).all()
#     data = [{
#         'Name': c.name,
#         'Contact': c.contact,
#         'Goal': c.goal,
#         'Weight': c.weight,
#         'Gender': c.gender,
#         'Type': c.client_type,
#         'Fees': c.fees,
#         'Payment Status': c.payment_status,
#         'Join Date': c.join_date,
#         'Due Date': c.payment_due_date,
#         'Last Updated': c.last_updated
#     } for c in clients]

#     os.makedirs('static/backups', exist_ok=True)
#     path = 'static/backups/master_clients.xlsx'
#     pd.DataFrame(data).to_excel(path, index=False)
#     return send_file(path, as_attachment=True)

# @app.route('/download_excel/<client_type>')
# def download_excel_by_type(client_type):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if client_type not in ['student', 'general']:
#         flash("Invalid client type!", 'danger')
#         return redirect(url_for('index'))

#     clients = Client.query.filter_by(client_type=client_type).all()
#     data = [{
#         'Name': c.name,
#         'Contact': c.contact,
#         'Goal': c.goal,
#         'Weight': c.weight,
#         'Gender': c.gender,
#         'Type': c.client_type,
#         'Fees': c.fees,
#         'Payment Status': c.payment_status,
#         'Join Date': c.join_date,
#         'Due Date': c.payment_due_date,
#         'Last Updated': c.last_updated
#     } for c in clients]

#     os.makedirs('static/backups', exist_ok=True)
#     path = f'static/backups/{client_type}_clients.xlsx'
#     pd.DataFrame(data).to_excel(path, index=False)
#     return send_file(path, as_attachment=True)

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)



# from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# from sqlalchemy import or_
# import pandas as pd
# import os

# app = Flask(__name__)
# app.config.update(
#     SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///clients.db'),
#     SECRET_KEY=os.getenv('SECRET_KEY', 'siva-secret'),
#     MAX_CONTENT_LENGTH=5 * 1024 * 1024
# )

# db = SQLAlchemy(app)

# UPLOAD_FOLDER = 'static/uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     gender = db.Column(db.String(10))
#     client_type = db.Column(db.String(20))
#     fees = db.Column(db.Integer)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date)
#     payment_due_date = db.Column(db.Date)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# @app.route('/')
# def root():
#     return redirect(url_for('home'))

# @app.route('/home')
# def home():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     next_3_days = today + timedelta(days=3)

#     total_clients = Client.query.count()
#     total_students = Client.query.filter_by(client_type='student').count()
#     total_general = Client.query.filter_by(client_type='general').count()

#     due_clients_count = Client.query.filter(
#         Client.payment_due_date <= next_3_days
#     ).count()

#     return render_template(
#         'home.html',
#         current_year=datetime.now().year,
#         total_clients=total_clients,
#         total_students=total_students,
#         total_general=total_general,
#         due_clients_count=due_clients_count
#     )

# @app.route('/index')
# def index():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     category = request.args.get('category')
#     query = request.args.get('search', '')

#     base_query = Client.query.filter(Client.payment_status == 'paid')

#     if category == 'student':
#         base_query = base_query.filter(Client.client_type == 'student')
#     elif category == 'general':
#         base_query = base_query.filter(Client.client_type == 'general')

#     if query:
#         base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

#     clients = base_query.all()

#     return render_template('paid_clients.html', clients=clients, query=query, category=category)

# @app.route('/paid')
# def paid_clients():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     query = request.args.get('search', '')
#     base_query = Client.query.filter_by(payment_status='paid')

#     if query:
#         base_query = base_query.filter(Client.name.ilike(f"%{query}%"))

#     clients = base_query.all()
#     return render_template('paid_clients.html', clients=clients, query=query)

# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         try:
#             name = request.form.get('name')
#             contact = request.form.get('contact')
#             gender = request.form.get('gender')
#             client_type = request.form.get('client_type')
#             join_date_str = request.form.get('join_date')
#             payment_status = request.form.get('payment_status')

#             if not all([name, contact, gender, client_type, join_date_str, payment_status]):
#                 flash("All required fields must be filled.", 'danger')
#                 return redirect(url_for('add_client'))

#             if not contact.isdigit() or len(contact) != 10:
#                 flash("Contact number must be exactly 10 digits.", 'danger')
#                 return redirect(url_for('add_client'))

#             join_date = datetime.strptime(join_date_str, "%Y-%m-%d").date()
#             due = join_date + timedelta(days=30)

#             goal = request.form.get('goal')
#             weight_str = request.form.get('weight')
#             weight = float(weight_str) if weight_str else None
#             if weight and (weight < 50 or weight > 110):
#                 flash("Weight must be between 50–110 kg.", 'danger')
#                 return redirect(url_for('add_client'))

#             fees_str = request.form.get('fees')
#             fees = int(fees_str) if fees_str and fees_str.isdigit() else 0

#             file = request.files.get('profile_image')
#             fname = None
#             if file and allowed_file(file.filename):
#                 fname = secure_filename(file.filename)
#                 file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

#             c = Client(
#                 name=name,
#                 contact=contact,
#                 goal=goal,
#                 weight=weight,
#                 gender=gender,
#                 client_type=client_type,
#                 fees=fees,
#                 payment_status=payment_status,
#                 join_date=join_date,
#                 payment_due_date=due,
#                 profile_image=fname,
#                 last_updated=datetime.now()
#             )
#             db.session.add(c)
#             db.session.commit()
#             flash("Client added!", 'success')
#             return redirect(url_for('index'))

#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             flash(f"Error: {e}", 'danger')
#             return redirect(url_for('add_client'))

#     return render_template('add_client.html')

# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)

#     if request.method == 'POST':
#         try:
#             client.name = request.form['name']
#             client.contact = request.form['contact']
#             client.goal = request.form['goal']
#             client.weight = float(request.form['weight']) if request.form.get('weight') else None
#             client.gender = request.form['gender']
#             client.client_type = request.form['client_type']
#             client.fees = int(request.form['fees']) if request.form.get('fees') else 0
#             client.payment_status = request.form['payment_status']
#             client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#             client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#             file = request.files.get('profile_image')
#             if file and allowed_file(file.filename):
#                 fname = secure_filename(file.filename)
#                 file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
#                 client.profile_image = fname

#             client.last_updated = datetime.now()
#             db.session.commit()
#             flash("Client updated!", 'success')
#             return redirect(url_for('index'))

#         except Exception as e:
#             flash(f"Error: {e}", 'danger')
#             return redirect(url_for('edit_client', client_id=client_id))

#     return render_template('edit_client.html', client=client)

# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     db.session.delete(Client.query.get_or_404(client_id))
#     db.session.commit()
#     flash("Client deleted.", 'info')
#     return redirect(url_for('index'))

# @app.route('/due')
# def due_clients():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     next_3_days = today + timedelta(days=3)

#     # ✅ Only update if status is still 'paid' and due soon
#     due_soon_clients = Client.query.filter(
#         Client.payment_due_date <= next_3_days,
#         Client.payment_status == 'paid'
#     ).all()

#     for client in due_soon_clients:
#         client.payment_status = 'unpaid'
#         client.last_updated = datetime.now()

#     db.session.commit()

#     # ✅ Now only fetch unpaid clients
#     due_clients = Client.query.filter(
#         Client.payment_status == 'unpaid',
#         Client.payment_due_date <= next_3_days
#     ).all()

#     return render_template('due_clients.html', clients=due_clients)


# @app.route('/mark_paid/<int:client_id>', methods=['POST'])
# def mark_paid(client_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     client.payment_status = 'paid'
#     client.last_updated = datetime.now()
#     db.session.commit()
#     flash(f"{client.name} marked as paid.", "success")
#     return redirect(url_for('due_clients'))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash("Invalid credentials", 'danger')
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash("Logged out", 'info')
#     return redirect(url_for('home'))
# @app.route('/master')
# def master_list():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     clients = Client.query.order_by(Client.join_date.desc()).all()
#     return render_template('master_list.html', clients=clients)

# @app.route('/download_excel_master')
# def download_excel_master():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     clients = Client.query.order_by(Client.join_date.desc()).all()
#     data = [{
#         'Name': c.name,
#         'Contact': c.contact,
#         'Goal': c.goal,
#         'Weight': c.weight,
#         'Gender': c.gender,
#         'Type': c.client_type,
#         'Fees': c.fees,
#         'Payment Status': c.payment_status,
#         'Join Date': c.join_date,
#         'Due Date': c.payment_due_date,
#         'Last Updated': c.last_updated
#     } for c in clients]

#     os.makedirs('static/backups', exist_ok=True)
#     path = 'static/backups/master_clients.xlsx'
#     pd.DataFrame(data).to_excel(path, index=False)

#     return send_file(path, as_attachment=True)


# @app.route('/download_excel_all')
# def download_excel_all():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     clients = Client.query.all()
#     data = [{
#         'Name': c.name,
#         'Contact': c.contact,
#         'Goal': c.goal,
#         'Weight': c.weight,
#         'Gender': c.gender,
#         'Type': c.client_type,
#         'Fees': c.fees,
#         'Payment Status': c.payment_status,
#         'Join Date': c.join_date,
#         'Due Date': c.payment_due_date,
#         'Last Updated': c.last_updated
#     } for c in clients]

#     os.makedirs('static/backups', exist_ok=True)
#     path = 'static/backups/all_clients.xlsx'
#     pd.DataFrame(data).to_excel(path, index=False)
#     return send_file(path, as_attachment=True)

# @app.route('/download_excel/<client_type>')
# def download_excel_by_type(client_type):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if client_type not in ['student', 'general']:
#         flash("Invalid client type!", 'danger')
#         return redirect(url_for('index'))

#     clients = Client.query.filter_by(client_type=client_type).all()
#     data = [{
#         'Name': c.name,
#         'Contact': c.contact,
#         'Goal': c.goal,
#         'Weight': c.weight,
#         'Gender': c.gender,
#         'Type': c.client_type,
#         'Fees': c.fees,
#         'Payment Status': c.payment_status,
#         'Join Date': c.join_date,
#         'Due Date': c.payment_due_date,
#         'Last Updated': c.last_updated
#     } for c in clients]

#     os.makedirs('static/backups', exist_ok=True)
#     path = f'static/backups/{client_type}_clients.xlsx'
#     pd.DataFrame(data).to_excel(path, index=False)
#     return send_file(path, as_attachment=True)

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)
