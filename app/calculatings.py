from datetime import datetime, timedelta

from sqlalchemy import func

from app.db.database import session_scope
from app.db.models import Book, OrderItem, Order, CartItem

from flask_login import current_user


def calculate_new_weekly_top():
    week = datetime.now() - timedelta(days=7)
    with session_scope() as session:
        session.query(Book).update({Book.in_top: False})

        top_books = session.query(OrderItem.book_id, func.sum(OrderItem.quantity).label('total_paid')).join(Order,
                                                                                                            Order.id == OrderItem.order_id).filter(
            Order.status == 'paid', Order.date >= week).group_by(OrderItem.book_id).order_by(
            func.sum(OrderItem.quantity).desc()).limit(3).all()

        for book_id, _ in top_books:
            book = session.get(Book, book_id)
            if book:
                book.in_top = True
        print(top_books)


def basket_calculating():
    with session_scope() as session:
        count = 0
        if current_user.is_authenticated:
            cart_items = session.query(CartItem).filter_by(user_id=current_user.id).all()
            count = sum(item.amount for item in cart_items)
    return count


# if __name__ == "__main__":
#     calculate_new_weekly_top()

