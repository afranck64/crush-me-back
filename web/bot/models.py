import datetime
import enum
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy as db

from .config import SQLALCHEMY_DATABASE_URI

Base = declarative_base()


ENGINE = None


class CrushState(enum.Enum):
    READY = "READY"
    MATCHED = "MATCHED"
    NOTIFIED = "NOTIFIED"
    DELETED = "DELETED"


class Crush(Base):
    __tablename__ = "crush"
    crusher = db.Column(db.String, primary_key=True)
    crushee = db.Column(db.String, primary_key=True)
    crushee_screen_name = db.Column(db.String)
    created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_on = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    message_id = db.Column(db.String)
    response_message_id = db.Column(db.String)
    matched = db.Column(db.Boolean, default=False)
    # notified = db.Column(db.Boolean, default=False)
    # deleted = db.Column(db.Boolean, default=False)
    state = db.Column(db.Enum(CrushState), default=CrushState.READY)

    # def __repr__(self) -> str:
    #     return f"Crush[{self.crusher} -> {self.crushee} ]"


# class Account(Base):
#     table_name = "account"
#     __name__ = table_name
#     __tablename__ = table_name
#     id = db.Column(db.Integer, primary_key=True)
#     active = db.Column(db.Boolean)
#     created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)
#     updated_on = db.Column(db.DateTime)

# class Link(Base):
#     __tablename__ = "link"
#     url = db.Column(db.String(256), primary_key=True)
#     is_online = db.Column(db.Boolean)
#     last_set_from_account_on = db.Column(db.DateTime)
#     last_checked_on = db.Column(db.DateTime)
#     last_online_on = db.Column(db.DateTime)
#     online_status_changed = db.Column(db.Boolean)
#     account_id = db.Column(db.Integer, db.ForeignKey('account.id', ondelete="CASCADE"), primary_key=True)


def get_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = db.create_engine(SQLALCHEMY_DATABASE_URI)
    return ENGINE


def get_connection():
    return get_engine().connect()


def get_session() -> Session:
    _session = sessionmaker(get_engine())
    return _session(bind=get_connection())


def get_connectable():
    return SQLALCHEMY_DATABASE_URI


def create_all():
    Base.metadata.create_all(get_engine())


def drop_all():
    engine = get_engine()
    Base.metadata.drop_all(engine)


def recreate_all():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
