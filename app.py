from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import os

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:///gym.db',
    SECRET_KEY='siva-secret',
    MAX_CONTENT_LENGTH=2 * 1024 * 1024
)

db = SQLAlchemy(app)
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    join_date = db.Column(db.Date, default=datetime.utcnow)
    payment_due_date = db.Column(db.Date, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    profile_image = db.Column(db.String(120), nullable=True)

@app.route('/')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    query = request.args.get('search', '')
    today = datetime.today().date()
    clients = (Client.query.filter(Client.name.ilike(f"%{query}%")).all()
               if query else Client.query.all())
    upcoming_due = Client.query.filter(
        Client.payment_status=='unpaid',
        Client.payment_due_date >= today,
        Client.payment_due_date <= today + timedelta(days=2)
    ).all()
    return render_template('clients.html', clients=clients, upcoming_due=upcoming_due, query=query)

@app.route('/add', methods=['GET','POST'])
def add_client():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    if request.method=='POST':
        try:
            name = request.form['name']
            contact = request.form['contact']
            goal = request.form['goal']
            weight = float(request.form['weight'])
            if weight < 50 or weight > 110:
                flash("Weight must be 50–110 kg", 'danger')
                return redirect(url_for('add_client'))
            gender = request.form['gender']
            client_type = request.form['client_type']
            fees = int(request.form['fees'])
            payment_status = request.form['payment_status']
            join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
            due = join_date + timedelta(days=30)
            file = request.files.get('profile_image')
            fname = None
            if file and allowed_file(file.filename):
                fname = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, fname))
            c = Client(
                name=name, contact=contact, goal=goal, weight=weight,
                gender=gender, client_type=client_type, fees=fees,
                payment_status=payment_status, join_date=join_date,
                payment_due_date=due, profile_image=fname,
                last_updated=datetime.now()
            )
            db.session.add(c); db.session.commit()
            flash("Client added!", 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error: {e}", 'danger')
            return redirect(url_for('add_client'))
    return render_template('add_client.html')

@app.route('/edit/<int:client_id>', methods=['GET','POST'])
def edit_client(client_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    client = Client.query.get_or_404(client_id)
    if request.method=='POST':
        try:
            client.name = request.form['name']
            client.contact = request.form['contact']
            client.goal = request.form['goal']
            client.weight = float(request.form['weight'])
            client.gender = request.form['gender']
            client.client_type = request.form['client_type']
            client.fees = int(request.form['fees'])
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
    due = Client.query.filter(
        Client.payment_status=='unpaid',
        Client.payment_due_date>=today,
        Client.payment_due_date<=today+timedelta(days=2)
    ).all()
    return render_template('due_clients.html', clients=due)

@app.route('/master')
def master_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('master_list.html', clients=Client.query.order_by(Client.join_date.desc()).all())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form['username']=='admin' and request.form['password']=='admin123':
            session['admin_logged_in']=True
            return redirect(url_for('home'))
        flash("Invalid credentials", 'danger')
    return render_template('login.html')

@app.route('/home')
def home():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html', current_year=datetime.now().year)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out", 'info')
    return redirect(url_for('login'))

@app.route('/download_excel')
def download_excel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    data = []
    for c in Client.query.all():
        data.append({
            'ID': c.id, 'Name': c.name, 'Contact': c.contact, 'Goal': c.goal,
            'Weight': c.weight, 'Gender': c.gender, 'Type': c.client_type,
            'Fees': c.fees, 'Status': c.payment_status,
            'Join Date': c.join_date, 'Due Date': c.payment_due_date,
            'Last Updated': c.last_updated
        })
    df = pd.DataFrame(data)
    os.makedirs('static/backups', exist_ok=True)
    path = 'static/backups/clients.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=10000)




# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # ✅ DB model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# # ✅ Home
# @app.route('/home')
# def home():
#     return render_template('home.html')

# # ✅ Login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == 'admin' and password == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash('Invalid credentials', 'danger')
#     return render_template('login.html')

# # ✅ Logout
# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash('Logged out successfully.', 'info')
#     return redirect(url_for('login'))

# # ✅ Index (main clients list)
# @app.route('/')
# def index():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all() if query else Client.query.all()

#     # Due in next 3 days
#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template("clients.html", clients=clients, upcoming_due=upcoming_due, query=query)

# # ✅ Add client
# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']

#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         filename = None
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             profile_image=filename,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('add_client.html')

# # ✅ Edit client
# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']

#         try:
#             client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         except:
#             pass

#         try:
#             client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()
#         except:
#             pass

#         file = request.files.get('profile_image')
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             client.profile_image = filename

#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('edit_client.html', client=client)

# # ✅ Delete client
# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# # ✅ Due clients within next 3 days
# @app.route('/due')
# def due_clients():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     due_clients = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template('due_clients.html', clients=due_clients)

# # ✅ Excel export
# @app.route('/download_excel')
# def download_excel():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     clients = Client.query.all()
#     data = [{
#         "ID": c.id,
#         "Name": c.name,
#         "Contact": c.contact,
#         "Goal": c.goal,
#         "Weight": c.weight,
#         "Payment Status": c.payment_status,
#         "Join Date": c.join_date.strftime('%Y-%m-%d'),
#         "Due Date": c.payment_due_date.strftime('%Y-%m-%d'),
#         "Last Updated": c.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
#     } for c in clients]

#     df = pd.DataFrame(data)
#     filepath = "static/backups/clients_backup.xlsx"
#     os.makedirs(os.path.dirname(filepath), exist_ok=True)
#     df.to_excel(filepath, index=False)

#     return send_file(filepath, as_attachment=True)

# # ✅ App run
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)



# from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# import pandas as pd
# import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# app.config['SECRET_KEY'] = 'siva-secret'

# UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# db = SQLAlchemy(app)

# # ✅ Helper function
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # ✅ Client model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# # ✅ Home page
# @app.route('/home')
# def home():
#     return render_template('home.html')

# # ✅ Login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == 'admin' and password == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash('Invalid credentials', 'danger')
#     return render_template('login.html')

# # ✅ Logout
# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash('Logged out successfully.', 'info')
#     return redirect(url_for('login'))

# # ✅ Index: Client list
# @app.route('/')
# def index():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     if query:
#         clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all()
#     else:
#         clients = Client.query.all()

#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template("clients.html", clients=clients, upcoming_due=upcoming_due, query=query)

# # ✅ Add client
# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']
#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         filename = None
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             profile_image=filename,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('add_client.html')

# # ✅ Edit client
# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']
#         client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             client.profile_image = filename

#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('edit_client.html', client=client)

# # ✅ Delete client
# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# # ✅ Due clients — updated logic to show only dues *after* 3 days
# @app.route('/due')
# def due_clients():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     # 🟢 Show clients whose due date is after 3 days from today
#     due_clients = Client.query.filter(Client.payment_due_date > today + timedelta(days=3)).all()

#     return render_template('due_clients.html', clients=due_clients)

# # ✅ Excel export
# @app.route('/download_excel')
# def download_excel():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     clients = Client.query.all()
#     data = [{
#         "ID": c.id,
#         "Name": c.name,
#         "Contact": c.contact,
#         "Goal": c.goal,
#         "Weight": c.weight,
#         "Payment Status": c.payment_status,
#         "Join Date": c.join_date.strftime('%Y-%m-%d'),
#         "Due Date": c.payment_due_date.strftime('%Y-%m-%d'),
#         "Last Updated": c.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
#     } for c in clients]

#     df = pd.DataFrame(data)
#     filepath = "static/backups/clients_backup.xlsx"
#     os.makedirs(os.path.dirname(filepath), exist_ok=True)
#     df.to_excel(filepath, index=False)

#     return send_file(filepath, as_attachment=True)


# # ✅ Run app
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)


# from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# import pandas as pd
# import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# app.config['SECRET_KEY'] = 'siva-secret'

# UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# db = SQLAlchemy(app)

# # ✅ Helper function to validate uploads
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # ✅ Model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# # ✅ Routes
# @app.route('/')
# def index():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     if query:
#         clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all()
#     else:
#         clients = Client.query.all()

#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template("clients.html", clients=clients, upcoming_due=upcoming_due, query=query)

# @app.route('/home')
# def home():
#     return render_template('home.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == 'admin' and password == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash('Invalid credentials', 'danger')
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash('Logged out successfully.', 'info')
#     return redirect(url_for('login'))

# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']
#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         filename = None
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             profile_image=filename,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('add_client.html')

# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']
#         client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             client.profile_image = filename

#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('edit_client.html', client=client)

# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# @app.route('/due')
# def due_clients():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     due_clients = Client.query.filter(Client.payment_due_date <= today + timedelta(days=3)).all()
#     return render_template('due_clients.html', clients=due_clients)

# # ✅ Excel Download Route
# @app.route('/download_excel')
# def download_excel():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     clients = Client.query.all()
#     data = [{
#         "ID": c.id,
#         "Name": c.name,
#         "Contact": c.contact,
#         "Goal": c.goal,
#         "Weight": c.weight,
#         "Payment Status": c.payment_status,
#         "Join Date": c.join_date.strftime('%Y-%m-%d'),
#         "Due Date": c.payment_due_date.strftime('%Y-%m-%d'),
#         "Last Updated": c.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
#     } for c in clients]

#     df = pd.DataFrame(data)
#     filepath = "static/backups/clients_backup.xlsx"
#     os.makedirs(os.path.dirname(filepath), exist_ok=True)
#     df.to_excel(filepath, index=False)

#     return send_file(filepath, as_attachment=True)

# # ✅ Backup Trigger Route
# @app.route('/trigger-backup')
# def trigger_backup():
#     import backup  # Ensure backup.py has a function, not just top-level code
#     backup.perform_backup()
#     return "Backup completed!"

# # ✅ Run
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)


##### working code #####

# from flask import Flask, render_template, request, redirect, url_for, session, flash
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# app.config['SECRET_KEY'] = 'siva-secret'

# UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# db = SQLAlchemy(app)

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # ✅ Model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# # ✅ Routes
# @app.route('/')
# def index():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     if query:
#         clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all()
#     else:
#         clients = Client.query.all()

#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template("clients.html", clients=clients, upcoming_due=upcoming_due, query=query)

# @app.route('/home')
# def home():
#     return render_template('home.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == 'admin' and password == 'admin123':
#             session['admin_logged_in'] = True
#             return redirect(url_for('home'))
#         flash('Invalid credentials', 'danger')
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     flash('Logged out successfully.', 'info')
#     return redirect(url_for('login'))

# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']
#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         filename = None
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             profile_image=filename,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('add_client.html')

# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']
#         client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             client.profile_image = filename

#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('edit_client.html', client=client)

# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# @app.route('/due')
# def due_clients():
#     if 'admin_logged_in' not in session:
#         return redirect(url_for('login'))

#     today = datetime.today().date()
#     due_clients = Client.query.filter(Client.payment_due_date <= today + timedelta(days=3)).all()
#     return render_template('due_clients.html', clients=due_clients)

# # ✅ Run
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(host='0.0.0.0', port=10000)

###############################################################################################################################
# from flask import Flask, render_template, request, redirect, url_for
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# from werkzeug.utils import secure_filename
# import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# app.config['SECRET_KEY'] = 'siva-secret'

# # ✅ File upload settings
# UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# db = SQLAlchemy(app)

# # ✅ Client model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)
#     profile_image = db.Column(db.String(120), nullable=True)

# # ✅ Home - List clients + search + stats
# @app.route('/')
# def index():
#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     if query:
#         clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all()
#     else:
#         clients = Client.query.all()

#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template("clients.html", clients=clients, upcoming_due=upcoming_due, query=query)

# # ✅ Add client
# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']
#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         filename = None
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             profile_image=filename,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))

#     return render_template('add_client.html')

# # ✅ Edit client
# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']
#         client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         file = request.files.get('profile_image')
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             client.profile_image = filename

#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('edit_client.html', client=client)

# # ✅ Delete client
# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# # ✅ Run app
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host='0.0.0.0', port=port)


#################################################################################

# from flask import Flask, render_template, request, redirect, url_for
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime, timedelta
# import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# app.config['SECRET_KEY'] = 'siva-secret'
# db = SQLAlchemy(app)

# # ✅ Client model
# class Client(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     contact = db.Column(db.String(20))
#     goal = db.Column(db.String(200))
#     weight = db.Column(db.Float)
#     payment_status = db.Column(db.String(20))
#     join_date = db.Column(db.Date, default=datetime.utcnow)
#     payment_due_date = db.Column(db.Date, default=datetime.utcnow)
#     last_updated = db.Column(db.DateTime, default=datetime.utcnow)

# # ✅ Home - List clients + search + stats
# @app.route('/')
# def index():
#     query = request.args.get('search', '')
#     today = datetime.today().date()

#     if query:
#         clients = Client.query.filter(Client.name.ilike(f"%{query}%")).all()
#     else:
#         clients = Client.query.all()

#     upcoming_due = Client.query.filter(
#         Client.payment_due_date >= today,
#         Client.payment_due_date <= today + timedelta(days=3)
#     ).all()

#     return render_template(
#         "clients.html",
#         clients=clients,
#         upcoming_due=upcoming_due,
#         query=query
#     )

# # ✅ Add client
# @app.route('/add', methods=['GET', 'POST'])
# def add_client():
#     if request.method == 'POST':
#         name = request.form['name']
#         contact = request.form['contact']
#         goal = request.form['goal']
#         weight = float(request.form['weight'])
#         payment_status = request.form['payment_status']
#         join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()

#         new_client = Client(
#             name=name,
#             contact=contact,
#             goal=goal,
#             weight=weight,
#             payment_status=payment_status,
#             join_date=join_date,
#             payment_due_date=payment_due_date,
#             last_updated=datetime.now()
#         )
#         db.session.add(new_client)
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('add_client.html')

# # ✅ Edit client
# @app.route('/edit/<int:client_id>', methods=['GET', 'POST'])
# def edit_client(client_id):
#     client = Client.query.get_or_404(client_id)
#     if request.method == 'POST':
#         client.name = request.form['name']
#         client.contact = request.form['contact']
#         client.goal = request.form['goal']
#         client.weight = float(request.form['weight'])
#         client.payment_status = request.form['payment_status']
#         client.join_date = datetime.strptime(request.form['join_date'], "%Y-%m-%d").date()
#         client.payment_due_date = datetime.strptime(request.form['payment_due_date'], "%Y-%m-%d").date()
#         client.last_updated = datetime.now()
#         db.session.commit()
#         return redirect(url_for('index'))
#     return render_template('edit_client.html', client=client)

# # ✅ Delete client
# @app.route('/delete/<int:client_id>', methods=['POST'])
# def delete_client(client_id):
#     client = Client.query.get_or_404(client_id)
#     db.session.delete(client)
#     db.session.commit()
#     return redirect(url_for('index'))

# # ✅ Run app
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host='0.0.0.0', port=port)


##########################################################################################################


# # from flask import Flask, render_template, request, redirect, url_for
# # from flask_sqlalchemy import SQLAlchemy
# # from datetime import datetime
# # import os

# # app = Flask(__name__)
# # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
# # app.config['SECRET_KEY'] = 'siva-secret'
# # db = SQLAlchemy(app)

# # # ✅ Define the Client model
# # class Client(db.Model):
# #     id = db.Column(db.Integer, primary_key=True)
# #     name = db.Column(db.String(100))
# #     contact = db.Column(db.String(20))
# #     goal = db.Column(db.String(200))
# #     weight = db.Column(db.Float)
# #     payment_status = db.Column(db.String(20))
# #     last_updated = db.Column(db.DateTime)

# # # ✅ Route: Home - List all clients
# # @app.route('/')
# # def index():
# #     clients = Client.query.all()
# #     return render_template("clients.html", clients=clients)

# # # ✅ Route: Add new client
# # @app.route('/add', methods=['GET', 'POST'])
# # def add_client():
# #     if request.method == 'POST':
# #         name = request.form['name']
# #         contact = request.form['contact']
# #         goal = request.form['goal']
# #         weight = float(request.form['weight'])
# #         payment_status = request.form['payment_status']
# #         new_client = Client(
# #             name=name,
# #             contact=contact,
# #             goal=goal,
# #             weight=weight,
# #             payment_status=payment_status,
# #             last_updated=datetime.now()
# #         )
# #         db.session.add(new_client)
# #         db.session.commit()
# #         return redirect(url_for('index'))
# #     return render_template('add_client.html')

# # # ✅ Run the app
# # if __name__ == '__main__':
# #     with app.app_context():
# #         db.create_all()  # Ensure the DB is created before running
# #     port = int(os.environ.get("PORT", 5000))
# #     app.run(host='0.0.0.0', port=port)
