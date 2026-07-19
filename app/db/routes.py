import os.path
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, SelectMultipleField, MultipleFileField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from app.db.database import session_scope
from app.db.models import User, Book, CartItem, OrderItem, Order

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


class ItemForm(FlaskForm):
    select_item = MultipleFileField()


class DeleteFromBasket(FlaskForm):
    delete_item = SubmitField('Delete')


# class DeliveryForm(FlaskForm):
#     address = StringField('Address', validators=[InputRequired()])


def basket_calculating():
    with session_scope() as session:
        count = 0
        if current_user.is_authenticated:
            cart_items = session.query(CartItem).filter_by(user_id=current_user.id).all()
            count = sum(item.amount for item in cart_items)
    return count


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

    count = basket_calculating()
    return render_template('main.html', books=books, genres=genres, form=form, count=count)


@main_blueprint.context_processor
def show_icons():
    def get_logos(directory):
        logos_list = []
        logos_dir = os.path.join('static', 'images', directory)
        if os.path.exists(logos_dir):
            logos = os.listdir(logos_dir)
            logos_list = [img for img in logos]
        return logos_list

    return dict(logos_list=get_logos)


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
                        or (book.description and searching in book.description.casefold())
                )
            ]
        for book in books:
            session.expunge(book)
        count = basket_calculating()
    return render_template('catalog.html', books=books, selected_genre=selected_genre, genres=genres,
                           searching_book=searching_book, form=form, count=count)


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
        book = None
        if book_id:
            book = session.query(Book).filter(Book.id == book_id).first()
            if book:
                session.expunge(book)
        cart_dict = {}
        if current_user.is_authenticated:
            cart_items = session.query(CartItem).filter_by(user_id=current_user.id).all()
            cart_dict = {item.book_id: item.amount for item in cart_items}
    count = basket_calculating()
    return render_template('specific_book.html', book=book, form=form, count=count, cart_dict=cart_dict)


@main_blueprint.route('/basket', methods=['GET', 'POST'])
@login_required
def show_basket():
    total_price = 0
    basket = []

    with session_scope() as session:
        order = session.query(Order).filter(Order.user_id == current_user.id, Order.status == 'new').first()
        if order:
            session.expunge(order)
        cart_items = session.query(CartItem, Book).join(Book, CartItem.book_id == Book.id).filter(
            CartItem.user_id == current_user.id).all()

        for cart_item, book in cart_items:
            session.expunge(book)
            basket.append({
                'amount': cart_item.amount,
                'title': book.title,
                'author': book.author,
                'price': book.price,
                'book_id': book.id
            })

    form = ItemForm()
    form.select_item.choices = [(str(item['book_id']), item['title']) for item in basket]

    if request.method == 'POST':
        selected_books = request.form.getlist('select_item')
        form.select_item.data = selected_books

        if selected_books:
            selected_books = [int(book) for book in selected_books]
            total_price = round(
                sum(item['price'] * item['amount'] for item in basket if item['book_id'] in selected_books),
                2
            )
            total_amount = sum(item['amount'] for item in basket if item['book_id'] in selected_books)
        else:
            total_price = 0
            total_amount = 0
    else:
        total_price = 0
        total_amount = 0
        form.select_item.data = []

    count = basket_calculating()

    return render_template('basket.html', form=form, basket=basket, total_price=total_price, count=count,
                           order=order, total_amount=total_amount)


@main_blueprint.route('/basket/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_from_basket(book_id):
    with session_scope() as session:
        cart_item = session.query(CartItem).filter_by(user_id=current_user.id, book_id=book_id).first()
        if cart_item:
            session.delete(cart_item)
    return redirect(url_for('main.show_basket'))


@main_blueprint.route('/orders')
@login_required
def show_orders():
    orders_list = []
    with session_scope() as session:
        orders = session.query(Order).filter(Order.user_id == current_user.id).all()
        for order in orders:
            orders_list.append(
                {'order_id': order.id,
                 'status': order.status,
                 'date': order.date,
                 'total_price': sum(item.price * item.quantity for item in order.order_items)}
            )
    count = basket_calculating()
    return render_template('my_orders.html', orders_list=orders_list, count=count)


@main_blueprint.route('/checkout', methods=['POST'])
@login_required
def complete_the_order():
    selected_books = request.form.getlist('select_item')
    if not selected_books:
        return redirect(url_for('main.show_basket'))

    selected_books_id = [int(book) for book in selected_books]
    with session_scope() as session:

        cart_items = session.query(CartItem, Book).join(Book, CartItem.book_id == Book.id).filter(
            CartItem.user_id == current_user.id, CartItem.book_id.in_(selected_books_id)).all()
        if not cart_items:
            return redirect(url_for('main.show_basket'))

        order = session.query(Order).filter(Order.user_id == current_user.id, Order.status == 'new').first()
        if not order:
            order = Order(
                user_id=current_user.id,
                date=datetime.now(),
                status='new',
                address=''
            )

            session.add(order)
            session.flush()

        for cart_item, book in cart_items:
            order_item = OrderItem(
                book=book,
                quantity=cart_item.amount,
                price=cart_item.amount * book.price
            )

            order.order_items.append(order_item)
            session.delete(cart_item)
        session.flush()
        order_id = order.id
    return redirect(url_for('main.current_order', order_id=order_id))


@main_blueprint.route('/checkout/current')
def current_order():
    with session_scope() as session:
        order = session.query(Order).filter(Order.user_id == current_user.id, Order.status == 'new').first()
        order_books = []
        for item in order.order_items:
            order_books.append({
                "title": item.book.title,
                "author": item.book.author,
                "quantity": item.quantity,
                "price": item.price,
                "total_book": item.price * item.quantity,
            })

        total_price = sum(book["total_book"] for book in order_books)
        delivery_date = order.date + timedelta(days=2)
        user = order.user.phone_number
        return render_template("current_order.html", order_books=order_books, order_number=order.id,
                               total_price=total_price, delivery_date=delivery_date, user=user)


@main_blueprint.route('/checkout/<int:order_id>/pay', methods=['POST'])
@login_required
def to_pay(order_id):
    with session_scope() as session:
        order = session.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = 'paid'
            order.address = request.form.get('address')
    return redirect(url_for('main.show_orders'))
