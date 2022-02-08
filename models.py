from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


class User(UserMixin, Base):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True)
  username = Column(String, nullable=False)
  reviews = relationship('Review', backref='users')
  password_hash = Column(String, nullable=False)

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)


class Book(Base):
  __tablename__ = 'books'
  isbn = Column(String(10), primary_key=True)
  title = Column(String(255), nullable=False)
  author = Column(String(255), nullable=False)
  year = Column(Integer, nullable=False)
  reviews = relationship('Review', backref='books')


class Review(Base):
  __tablename__ = 'reviews'
  id = Column(Integer, primary_key=True)
  content = Column(String(255), nullable=True)
  rating = Column(Integer, nullable=False)
  date = Column(DateTime, nullable=False)
  user_id = Column(Integer, ForeignKey('users.id'))
  book_id = Column(String(10), ForeignKey('books.isbn'))
