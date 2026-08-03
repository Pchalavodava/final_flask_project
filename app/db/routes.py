import os.path
import random
from datetime import datetime, timedelta
from flask import abort

from flask import Blueprint, flash, redirect, render_template, url_for, request, session as f_session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, TextAreaField, MultipleFileField, RadioField
from wtforms.validators import Email, EqualTo, InputRequired, Length, DataRequired

from app.db.database import session_scope
from app.db.models import User, Book, CartItem, OrderItem, Order, Review

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import func

from app.calculatings import basket_calculating

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


class FeedbackForm(FlaskForm):
    review = TextAreaField('Your review:', validators=[Length(max=400, message='You can write 400 symbols only')])
    rating = RadioField(choices=[('1', '1☆'), ('2', '2☆'), ('3', '3☆'), ('4', '4☆'), ('5', '5☆')],
                        validators=[DataRequired(message='Choose please')])
    submit = SubmitField('Send a review')


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

        f_session['user_name'] = request.form.get('username')
        f_session['phone_number'] = request.form.get('phone_number')
        f_session['email'] = request.form.get('email')
        f_session['password'] = request.form.get('password')

        sms_code = random.randint(1000, 9999)
        f_session['sms_code'] = sms_code
        return redirect(url_for('main.verify_register'))
    return render_template('register.html', form=form)


@main_blueprint.route('/register/verify', methods=['GET', 'POST'])
def verify_register():
    server_code = int(f_session.get('sms_code'))
    if request.method == 'POST':
        user_code = int(request.form.get('sms_code'))
        if user_code == server_code:
            with session_scope() as session:
                user = User(
                    username=f_session.get('user_name'),
                    phone_number=f_session.get('phone_number'),
                    email=f_session.get('email').lower().strip(),
                    password_hash=generate_password_hash(f_session.get('password'))
                )
                session.add(user)
            f_session.pop('user_name', None)
            f_session.pop('phone_number', None)
            f_session.pop('email', None)
            f_session.pop('password', None)
            f_session.pop('sms_code', None)
            flash('Registration successful', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Incorrect SMS-code. Try again', 'danger')
    return render_template('verify.html', server_code=server_code)


@main_blueprint.route('/', methods=['GET', 'POST'])
def main_route():
    form = SearchForm()
    with session_scope() as session:
        books = session.query(Book).filter(Book.in_top.is_(True)).all()
        if not books:
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
                f_session['login_user_id'] = user.id
                sms_code = random.randint(1000, 9999)
                f_session['sms_code'] = sms_code
                return redirect(url_for('main.verify_login'))
            flash('Login failed', 'danger')
            return redirect(url_for('main.login'))
    return render_template('login.html', form=form)


@main_blueprint.route('/login/verify', methods=['GET', 'POST'])
def verify_login():
    server_code = int(f_session.get('sms_code'))
    if request.method == 'POST':
        user_code = int(request.form.get('sms_code'))
        if user_code == server_code:
            with session_scope() as session:
                user_id = f_session.get('login_user_id')
                user = session.query(User).get(user_id)
                if user:
                    login_user(user)
                    flash('Welcome', 'success')
                    f_session.pop('sms_code', None)
                    f_session.pop('login_user_id', None)
                    return redirect(url_for('main.main_route'))
        else:
            flash('Incorrect SMS-code. Try again', 'danger')
    return render_template('verify.html', server_code=server_code)


@main_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out', 'success')
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
                if (searching in book.title.casefold()
                    or searching in book.author.casefold()
                    or searching in book.genre.casefold()
                    or (book.description and searching in book.description.casefold()))
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
                cart_item = CartItem(user_id=current_user.id, book_id=book_id, amount=1)
                session.add(cart_item)
        flash('You have successfully added the book to your basket', 'success')
        return redirect(url_for('main.show_book', book_id=book_id))
    book_dict = {}
    cart_dict = {}
    paid_books_id = []
    rated_books_id = []
    with session_scope() as session:
        book = None
        if book_id:
            book = session.query(Book).filter(Book.id == book_id).first()
        book_dict = {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'year': book.year,
            'price': book.price,
            'description': book.description,
            'rating': book.rating
        }
        if current_user.is_authenticated:
            cart_items = session.query(CartItem).filter_by(user_id=current_user.id).all()
            cart_dict = {item.book_id: item.amount for item in cart_items}

            purchased_books = session.query(OrderItem).join(Order).filter(Order.user_id == current_user.id,
                                                                          Order.status == 'paid').all()
            paid_books_id = [purchased_book.book_id for purchased_book in purchased_books]

            rated_books = session.query(Review).filter(Review.user_id == current_user.id).all()
            rated_books_id = [rated_book.book_id for rated_book in rated_books]

        if book and book in session:
            session.expunge(book)

    count = basket_calculating()
    return render_template('specific_book.html', book=book_dict, form=form, count=count, cart_dict=cart_dict,
                           paid_books_id=paid_books_id, rated_books_id=rated_books_id)


@main_blueprint.route('/basket', methods=['GET', 'POST'])
@login_required
def show_basket():
    total_price = 0
    basket = []

    with session_scope() as session:
        order = session.query(Order).filter(Order.user_id == current_user.id, Order.status == 'new').first()
        if order is not None:
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
                'book_id': book.id,
                'book_image': book.cover_url
            })

    form = ItemForm()
    form.select_item.choices = [(str(item['book_id']), item['title']) for item in basket]

    if request.method == 'POST':
        selected_books = request.form.getlist('select_item')
        form.select_item.data = selected_books
        if selected_books:
            selected_books = [int(book) for book in selected_books]
            total_price = round(
                sum(item['price'] * item['amount'] for item in basket if item['book_id'] in selected_books), 2)
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
    flash(f'Book {book_id} was successfully removed', 'danger')
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
                 'total_price': round(sum(item.price for item in order.order_items), 2)}
            )
    count = basket_calculating()
    return render_template('my_orders.html', orders_list=orders_list, count=count)


@main_blueprint.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def show_order(order_id):
    order_items = []
    with session_scope() as session:
        order = session.query(Order).filter(Order.user_id == current_user.id, Order.id == order_id).first()
        if not order:
            abort(404)
        for order_item in order.order_items:
            order_items.append(
                {
                    'book_title': order_item.book.title,
                    'count': order_item.quantity,
                    'price': order_item.price
                }
            )
        order_details = {
            'order_number': order_id,
            'date': order.date,
            'status': order.status,
            'total_price': round(sum(item['price'] for item in order_items), 2),
            'customer_name': order.customer_name,
            'address': order.address,
            'phone_number': order.user.phone_number,
        }
    return render_template('show_order.html', order_items=order_items, order_details=order_details)


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
            order = Order(user_id=current_user.id, date=datetime.now(), status='new', address='')
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
@login_required
def current_order():
    with session_scope() as session:
        order = session.query(Order).filter(Order.user_id == current_user.id, Order.status == 'new').first()
        order_books = []
        for item in order.order_items:
            order_books.append({
                "title": item.book.title,
                "author": item.book.author,
                "quantity": item.quantity,
                "price": item.book.price,
                "total_item_price": item.quantity * item.book.price
            })
        total_price = sum(book["total_item_price"] for book in order_books)
        delivery_date = order.date + timedelta(days=2)
        user = order.user.phone_number
        return render_template("current_order.html", order_books=order_books, order_number=order.id,
                               total_price=total_price, delivery_date=delivery_date, user=user)


@main_blueprint.route('/checkout/<int:order_id>/pay', methods=['POST'])
@login_required
def to_pay(order_id):
    order_number = ''
    with session_scope() as session:
        order = session.query(Order).filter(Order.id == order_id).first()
        if not order:
            abort(404)

        if order.user_id != current_user.id:
            abort(403)

        order.status = 'paid'
        order.address = request.form.get('address')
        order.customer_name = request.form.get('name') + ' ' + request.form.get('surname')
        order_number = order.id
    flash(f'Order №{order_number} has been paid', 'success')
    return redirect(url_for('main.show_orders'))


@main_blueprint.route('/checkout/<int:order_id>/cancel')
@login_required
def cancel_order(order_id):
    order_number = ''
    with session_scope() as session:
        order_to_delete = session.query(Order).filter(Order.id == order_id).first()
        if not order_to_delete:
            abort(404)

        if order_to_delete.user_id != current_user.id:
            abort(403)

        order_to_delete.status = 'rejected'
        order_number = order_to_delete.id
    flash(f'Order №{order_number} has been rejected', 'danger')
    return redirect(url_for('main.show_orders'))


@main_blueprint.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def write_a_review(book_id):
    with session_scope() as session:
        book = session.query(Book).filter(Book.id == book_id).first()
        book = {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'genre': book.genre,
            'rating': book.rating
        }
    form = FeedbackForm()
    return render_template("review.html", book=book, form=form)


@main_blueprint.route('/review/<int:book_id>/send', methods=['POST'])
@login_required
def send_a_review(book_id):
    form = FeedbackForm()
    book_data = None
    with session_scope() as session:
        book = session.query(Book).filter(Book.id == book_id).first()

        if form.validate_on_submit():
            review = Review(review_text=form.review.data, user_id=current_user.id, book_id=book_id,
                            stars=int(form.rating.data))
            session.add(review)
            session.flush()

            book_rating_count = session.query(func.count(Review.id)).filter(Review.book_id == book_id).scalar()
            new_star = int(form.rating.data)
            if book.rating and book_rating_count == 1:
                book.rating = (book.rating + new_star) / (book_rating_count + 1)
            elif book.rating and book_rating_count > 1:
                total_rating_count = book_rating_count + 1
                total_rating = book.rating * book_rating_count + new_star
                book.rating = round(total_rating / total_rating_count, 1)
            else:
                book.rating = float(new_star)
            book_data = {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'genre': book.genre,
                'rating': book.rating
            }
            return render_template('review.html', book=book, form=form)
        book_data = {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'genre': book.genre,
            'rating': book.rating
        }
        return render_template("review.html", book=book_data, form=form)
