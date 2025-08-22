from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_PATH = "sqlite:///settings.db"
Base = declarative_base()

class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String)


from sqlalchemy import Integer, DateTime
import datetime

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String)
    amount = Column(Integer)
    description = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def add_payment_transaction(order_id, amount, description, status):
    session = SessionLocal()
    tx = PaymentTransaction(order_id=order_id, amount=amount, description=description, status=status)
    session.add(tx)
    session.commit()
    session.close()

def get_all_transactions():
    session = SessionLocal()
    txs = session.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).all()
    session.close()
    return txs

def get_setting(key: str) -> str:
    session = SessionLocal()
    setting = session.query(Settings).filter_by(key=key).first()
    session.close()
    return setting.value if setting else ""

def set_setting(key: str, value: str):
    session = SessionLocal()
    setting = session.query(Settings).filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        session.add(setting)
    session.commit()
    session.close()
