from flask import Flask, render_template, redirect, url_for
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from wtforms import PasswordField, StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import EmailField
from flask_socketio import SocketIO
from data import db_session, users
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
app.config.update(dict(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='yandexlyceumchat@gmail.com',
    MAIL_PASSWORD='root$ylchat',
    MAIL_DEFAULT_SENDER='yandexlyceumchat@gmail.com',
    MAIL_SUPPRESS_SEND=False,
    TESTING=False
))
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
mail = Mail()
mail.init_app(app)


class LoginForm(FlaskForm):
    nick = StringField('Nick:', validators=[DataRequired()])
    password = PasswordField('Password:', validators=[DataRequired()])
    remember_me = BooleanField('Remember me', default=False)
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    nick = StringField('Nick:', validators=[DataRequired()])
    email = EmailField('Email:', validators=[DataRequired()])
    password = PasswordField('Password:', validators=[DataRequired()])
    password_again = PasswordField('Password again:', validators=[DataRequired()])
    submit = SubmitField('Register')


class RequestResetPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password_again = PasswordField('Repeat Password', validators=[DataRequired()])
    submit = SubmitField('Reset password')


@app.route('/')
def sessions():
    return render_template('index.html', title='Chat')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(users.User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Passwords don't match!")
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.email.data).first() or (
                session.query(users.User).filter(users.User.nick == form.nick.data).first()
        ):
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="User already exists!")
        user = users.User(
            nick=form.nick.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Registration', form=form, message='')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.nick == form.nick.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               title='Login',
                               message="Wrong login or password!",
                               form=form)
    return render_template('login.html', title='Login', form=form, message='')


def message_received(methods=['GET', 'POST']):
    print('message was received!!!')


@app.errorhandler(404)
def handler(e):
    return render_template('info_page.html', title='Not found', message="Oops! This page doesn't exist.")


@app.errorhandler(500)
def handler(e):
    return render_template('info_page.html', title='Error', message="Oops! An unexpected error happened.")


@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    socketio.emit('my response', json, callback=message_received)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect('/')
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            msg = Message("YlChat Password Reset",
                          recipients=[user.email])
            msg.html = render_template("email_template.html", token=token, user=user)
            mail.send(msg)
            return render_template('info_page.html', title='Instructions', message="Check your email for a letter.")
        else:
            return render_template('reset_password_request.html',
                                   title='Reset Password', form=form, message='No user with such email!')
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form, message='')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('/'))
    session = db_session.create_session()
    user = users.User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('/'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        session.query(users.User).filter(users.User.id == user.id).first().set_password(form.password.data)
        session.commit()
        return render_template("info_page.html", title="Success", message='Your password was reset successfully.')
    return render_template('reset_password.html', form=form, title='Reset Password')


if __name__ == '__main__':
    db_session.global_init("db/chat.sqlite")
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
