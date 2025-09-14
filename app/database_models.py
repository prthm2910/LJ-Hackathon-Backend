from sqlalchemy import Column, String, Integer, Boolean, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base

# Base class for all our database models
Base = declarative_base()

class User(Base):
    # The __tablename__ attribute tells SQLAlchemy the name of the table in the DB.
    __tablename__ = 'users'
    
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    credit_score = Column(Integer)
    epf_balance = Column(Float)

    # AI Permission Controls
    perm_assets = Column(Boolean, default=True)
    perm_liabilities = Column(Boolean, default=True) 
    perm_transactions = Column(Boolean, default=True)
    perm_investments = Column(Boolean, default=True)
    perm_credit_score = Column(Boolean, default=True)
    perm_epf_balance = Column(Boolean, default=True)

class Asset(Base):
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)
    value = Column(Float, nullable=False)

class Liability(Base):
    __tablename__ = 'liabilities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)
    outstanding_balance = Column(Float, nullable=False)

class Investment(Base):
    __tablename__ = 'investments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    ticker = Column(String)
    type = Column(String)
    quantity = Column(Float)
    current_value = Column(Float, nullable=False)

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
