from flask import Flask, render_template, redirect
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, login_required, logout_user
from wtforms import PasswordField, StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import EmailField
from werkzeug.exceptions import NotFound
from flask_socketio import SocketIO
from data import db_session, users

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)


class LoginForm(FlaskForm):
    nick = StringField('Ник', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня', default=False)
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    nick = StringField('Никнейм', validators=[DataRequired()])
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')


@app.route('/')
def sessions():
    return render_template('index.html', title='Добро пожаловать!')


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
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.email.data).first() or (
                session.query(users.User).filter(users.User.nick == form.nick.data).first()
        ):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = users.User(
            nick=form.nick.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form, message='')


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
                               title='Вход',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Вход', form=form, message='')


def message_received(methods=['GET', 'POST']):
    print('message was received!!!')


@app.errorhandler(404)
def handler(e):
    return redirect('/')


@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    socketio.emit('my response', json, callback=message_received)


if __name__ == '__main__':
    db_session.global_init("db/chat.sqlite")
    socketio.run(app, host='0.0.0.0')
