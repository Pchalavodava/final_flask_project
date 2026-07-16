from datetime import datetime

from flask_login import UserMixin
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class User(Base, UserMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(256))

    orders: Mapped[list['Order']] = relationship(back_populates='user')
    cart_items: Mapped[list['CartItem']] = relationship(back_populates='user')
    reviews: Mapped[list['Review']] = relationship(back_populates='user')


class Book(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    author: Mapped[str] = mapped_column(String(120))
    price: Mapped[float]
    genre: Mapped[str] = mapped_column(String(50))
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    cart_items: Mapped[list['CartItem']] = relationship(back_populates='book')
    order_items: Mapped[list['OrderItem']] = relationship(back_populates='book')
    reviews: Mapped[list['Review']] = relationship(back_populates='book')


class CartItem(Base):
    __tablename__ = 'cart_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'))
    amount: Mapped[int]

    user: Mapped['User'] = relationship(back_populates='cart_items')
    book: Mapped['Book'] = relationship(back_populates='cart_items')


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    date: Mapped[datetime] = mapped_column(default=datetime.now)
    status: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(100))

    order_items: Mapped[list['OrderItem']] = relationship(back_populates='order')
    user: Mapped['User'] = relationship(back_populates='orders')


class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'))
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'))
    quantity: Mapped[int]
    price: Mapped[int]

    order: Mapped['Order'] = relationship(back_populates='order_items')
    book: Mapped['Book'] = relationship(back_populates='order_items')


class Review(Base):
    __tablename__ = 'reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    review_text: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    book_id: Mapped[int] = mapped_column((ForeignKey('books.id')))
    stars: Mapped[int]

    user: Mapped['User'] = relationship(back_populates='reviews')
    book: Mapped['Book'] = relationship(back_populates='reviews')