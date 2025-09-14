from sqlalchemy import Column, String, Integer, Boolean, Float, Date, ForeignKey # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore

Base = declarative_base()

class User(Base):
    _tablename_ = 'users'
    
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    credit_score = Column(Integer, nullable=False)
    epf_balance = Column(Float, nullable=False)

    # AI Permission Controls 🤖🔐
    perm_assets = Column(Boolean, default=True)
    perm_liabilities = Column(Boolean, default=True) 
    perm_transactions = Column(Boolean, default=True)
    perm_investments = Column(Boolean, default=True)
    perm_credit_score = Column(Boolean, default=True)
    perm_epf_balance = Column(Boolean, default=True)

class Asset(Base):
    _tablename_ = 'assets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    value = Column(Float, nullable=False)

class Liability(Base):
    _tablename_ = 'liabilities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    outstanding_balance = Column(Float, nullable=False)

class Investment(Base):
    _tablename_ = 'investments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)

class Transaction(Base):
    _tablename_ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)