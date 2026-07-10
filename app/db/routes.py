from flask import Blueprint, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from app.db.database import session_scope
from app.db.models import User, Book, CartItem

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import or_, func

main_blueprint = Blueprint('main', __name__)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=36)])


class RegistrationForm(FlaskForm):
    username = StringField('User Name', validators=[InputRequired(), Length(min=4, max=100)])
    phone_number = StringField('Phone number', validators=[InputRequired(), Length(min=10, max=20)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=36)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])


class SearchForm(FlaskForm):
    query = StringField('Search', validators=[InputRequired()])
    submit = SubmitField('Search')


class AddToCartForm(FlaskForm):
    submit = SubmitField('AddToCart')


@main_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        with session_scope() as session:
            user = session.query(User).filter_by(email=form.email.data).first()
            username = session.query(User).filter_by(username=form.username.data).first()
        if user:
            flash('User with this email already exists!', 'danger')
            return redirect(url_for('main.register'))
        if username:
            flash('User name already exists!', 'danger')
            return redirect(url_for('main.register'))

        user = User(
            username=form.username.data,
            phone_number=form.phone_number.data,
            email=form.email.data.lower().strip(),
            password_hash=generate_password_hash(form.password.data)
        )
        with session_scope() as session:
            session.add(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('main.login'))
    elif form.errors:
        flash(form.errors, category='danger')

    return render_template('register.html', form=form)


@main_blueprint.route('/', methods=['GET', 'POST'])
# @login_required
def main_route():
    form = SearchForm()
    with session_scope() as session:
        books = session.query(Book).order_by(Book.rating.desc()).limit(3).all()
        for book in books:
            session.expunge(book)
        genres = session.query(Book.genre).distinct().order_by(Book.genre).all()
    return render_template('main.html', books=books, genres=genres, form=form)


@main_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with session_scope() as session:
            email = form.email.data.lower().strip()
            user = session.query(User).filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                user_id = user.id
                login_user(user)
                # login_user(user, remember=True)
                return redirect(url_for('main.main_route'))
            flash('Login failed', 'danger')
    return render_template('login.html', form=form)


@main_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.main_route'))


@main_blueprint.route('/catalog', methods=['GET', 'POST'])
def show_catalog():
    form = SearchForm()
    searching_book = ''
    if form.validate_on_submit():
        searching_book = form.query.data.strip()

    selected_genre = request.args.get('genre')

    with session_scope() as session:

        genres = session.query(Book.genre).distinct().order_by(Book.genre).all()
        query = session.query(Book)

        if selected_genre:
            query = query.filter(Book.genre == selected_genre)

        books = query.all()

        if searching_book:
            searching = searching_book.casefold()

            books = [
                book for book in books
                if (
                        searching in book.title.casefold()
                        or searching in book.author.casefold()
                        or searching in book.genre.casefold()
                        or (Book.description and searching in book.description.casefold())
                )
            ]
        for book in books:
            session.expunge(book)

    return render_template('catalog.html', books=books, selected_genre=selected_genre, genres=genres,
                           searching_book=searching_book, form=form)


@main_blueprint.route('/book/<int:book_id>', methods=['GET', 'POST'])
def show_book(book_id):
    form = AddToCartForm()
    if form.validate_on_submit():
        with session_scope() as session:
            item = session.query(CartItem).filter_by(
                user_id=current_user.id,
                book_id=book_id
            ).first()

            if item:
                item.amount += 1
            else:
                cart_item = CartItem(
                    user_id=current_user.id,
                    book_id=book_id,
                    amount=1
                )
                session.add(cart_item)
        return redirect(url_for('main.show_book', book_id=book_id))

    with session_scope() as session:
        count = 0
        book = None
        if book_id:
            book = session.query(Book).filter(Book.id == book_id).first()
            if book:
                session.expunge(book)
        if current_user.is_authenticated:
            cart_items = session.query(CartItem).filter_by(user_id=current_user.id).all()
            count = sum(item.amount for item in cart_items)
    return render_template('specific_book.html', book=book, form=form, count=count)

    # with session_scope() as session:
    #     book = None
    #     if book_id:
    #         book = session.query(Book).filter(Book.id == book_id).first()
    #         if book:
    #             session.expunge(book)
    # return render_template('specific_book.html', book=book, form=form)
