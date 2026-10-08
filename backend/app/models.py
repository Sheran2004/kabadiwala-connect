import time, uuid
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
uid = lambda: uuid.uuid4().hex
def col_id(n=32): return mapped_column(String(n), primary_key=True, default=uid)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = col_id()
    phone: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    role: Mapped[str] = mapped_column(String(10))            # collector | recycler | admin
    pw_hash: Mapped[str] = mapped_column(String(128))
    salt: Mapped[str] = mapped_column(String(32))
    created: Mapped[float] = mapped_column(Float, default=time.time)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)   # recyclers need admin approval to bid
    verified_at: Mapped[float] = mapped_column(Float, nullable=True)

class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    kg: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(10), default="open", index=True)   # open | sold | cancelled
    created: Mapped[float] = mapped_column(Float, default=time.time)
    lat: Mapped[float] = mapped_column(Float, nullable=True)
    lng: Mapped[float] = mapped_column(Float, nullable=True)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    pickup_date: Mapped[str] = mapped_column(String(10), nullable=True)
    pickup_slot: Mapped[str] = mapped_column(String(10), nullable=True)

class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (UniqueConstraint("lot_id", "buyer_id"),)
    id: Mapped[str] = col_id()
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[str] = col_id()
    lot_id: Mapped[str] = mapped_column(String(12))
    seller_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    kg: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    stage: Mapped[str] = mapped_column(String(12), default="scheduled")        # scheduled -> on_the_way -> picked_up (set by the buyer)
    stage_at: Mapped[float] = mapped_column(Float, nullable=True)
    pay_status: Mapped[str] = mapped_column(String(10), default="pending")     # pending -> sent (buyer) -> confirmed (seller)
    pay_method: Mapped[str] = mapped_column(String(8), nullable=True)
    pay_ref: Mapped[str] = mapped_column(String(40), nullable=True)
    pay_at: Mapped[float] = mapped_column(Float, nullable=True)

class Rate(Base):
    __tablename__ = "rates"
    type: Mapped[str] = mapped_column(String(10), primary_key=True)
    price: Mapped[float] = mapped_column(Float)
    updated: Mapped[float] = mapped_column(Float, default=time.time)
    by_id: Mapped[str] = mapped_column(String(32), nullable=True)

class RateReport(Base):
    __tablename__ = "rate_reports"
    id: Mapped[str] = col_id()
    type: Mapped[str] = mapped_column(String(10), index=True)
    price: Mapped[float] = mapped_column(Float)
    by_id: Mapped[str] = mapped_column(String(32))
    created: Mapped[float] = mapped_column(Float, default=time.time, index=True)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = col_id()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    data: Mapped[str] = mapped_column(String(300))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Otp(Base):
    __tablename__ = "otps"
    id: Mapped[str] = col_id()
    phone: Mapped[str] = mapped_column(String(10), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("sale_id", "from_id"),)
    id: Mapped[str] = col_id()
    sale_id: Mapped[str] = mapped_column(ForeignKey("sales.id"), index=True)
    from_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    to_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    stars: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(200), default="")
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = col_id()
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    receiver_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(500))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=time.time)
