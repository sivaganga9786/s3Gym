@app.route('/home')
def home():
    return render_template('home.html')



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

# # ✅ View due clients
# @app.route('/due')
# def due_clients():
#     today = datetime.today().date()
#     due_clients = Client.query.filter(Client.payment_due_date <= today + timedelta(days=3)).all()
#     return render_template('due_clients.html', clients=due_clients)

# # ✅ Run app
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host='0.0.0.0', port=port)


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
