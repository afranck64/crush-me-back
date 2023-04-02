import datetime
import enum
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import UniqueConstraint
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
    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    crusher = db.Column(db.String)
    crushee = db.Column(db.String)
    crushee_screen_name = db.Column(db.String)
    created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_on = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    message_id = db.Column(db.String)
    response_message_id = db.Column(db.String)
    matched = db.Column(db.Boolean, default=False)
    state = db.Column(db.Enum(CrushState), default=CrushState.READY)

    __table_args__ = (
        UniqueConstraint("crusher", "crushee", name="crusher_crusheed_unique_constraint"),
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"Crush[{self.crusher} @ {self.crushee}]"


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
