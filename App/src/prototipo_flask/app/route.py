
import os

from flask import (flash, redirect, render_template, request, send_file,
                   send_from_directory, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

from app import app, db
from app.conversor import (configuration_table, genera_dxf,
                           get_errors_rectangle, get_errors_square,
                           get_errors_upload, get_layers, upload_txt)
from app.forms import LoginForm, RegistrationForm
from app.models import User
from app.upload_optional_files import extract_symbols, upload_file_config

ALLOWED_EXTENSIONS = set(["txt", "csv"])
errores = []
capas = []


def allowed_file(filename):
    return "." in filename and filename.rsplit(
        ".", 1)[1].lower() in ALLOWED_EXTENSIONS


db.create_all()


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('upload_file'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Error: Invalid email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('upload_file')
            flash('User successfully logged in')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('upload_file'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "POST":
        if "file_surveying" not in request.files:
            flash("Error: topographic data file not selected.")
        if "file_config" not in request.files:
            f_config = ""
        else:
            f_config = request.files["file_config"]
        f = request.files["file_surveying"]
        if f.filename == "":
            flash("Error: topographic data file not selected.")
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)

            if f_config and allowed_file(f_config.filename):
                filename_config = secure_filename(f_config.filename)
                f_config.save(os.path.join(
                    app.config["UPLOAD_FOLDER"], filename_config))
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            # Se genera y se guarda el archivo dxf
            upload_txt("./tmp/" + filename)
            extract_symbols()
            if f_config!="":
                upload_file_config("./tmp/" + filename_config)
            configuration_table()
            # os.remove("./tmp/"+filename)
            if get_errors_upload():
                flash(
                    'Error: topographic data file has the following errors. \
                         Check the file')
                return render_template('upload.html', title='Carga Archivos')
            if get_errors_square():
                flash(
                    'Error: The number of points with "TC" code is not \
                        multiple of 2. Check the file')
                return render_template('upload.html', title='Carga Archivos')
            if get_errors_rectangle():
                flash(
                    'Error: The number of points with "TR" code is not \
                        multiple of 3. Check the file')
                return render_template('upload.html', title='Carga Archivos')

            
            return redirect(url_for("convert_file_dxf"))
        flash("Error: the topografic data file type must be: .txt o .csv.")
    return render_template('upload.html', title='Carga Archivos')


@app.route("/convert", methods=["GET", "POST"])
@login_required
def convert_file_dxf():
    if request.method == "POST":
        
        # Provisional
        genera_dxf("./tmp","salida.dxf",configuration_table())

        return redirect(url_for("downloads"))
    return render_template(
        'convert.html',
        title='Conversion DXF',
        capas=get_layers(),
        errores=get_errors_upload())


@app.route("/download", methods=["GET", "POST"])
@login_required
def downloads():
    if request.method == "POST":
        return redirect(url_for("download_file", filename='salida.dxf'))
    return render_template('download.html')


@app.route('/download_files/<filename>')
@login_required
def download_file(filename):
    try:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            filename,
            as_attachment=True)
    except Exception as e:
        return str(e)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
