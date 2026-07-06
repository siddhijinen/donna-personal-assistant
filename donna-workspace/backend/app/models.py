import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, Text, Float

def get_utc_now():
    """Generates a correct, modern timezone-naive UTC timestamp."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

# The single source of truth for Base lives right here
class Base(DeclarativeBase):
    pass

class UserData(Base):
    """Isolated operational table for user data processing."""
    __tablename__ = "user_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key_param: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    value_data: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, onupdate=get_utc_now
    )

class WriteOnlyAuditLog(Base):
    """Compliance Audit Log Table. Append-only."""
    __tablename__ = "write_only_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)
    agent_name: Mapped[str] = mapped_column(String(100))
    action_executed: Mapped[str] = mapped_column(Text)
    hitl_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    security_flag: Mapped[bool] = mapped_column(Boolean, default=False)

class CalendarEvent(Base):
    """Day 8: Unified Calendar Storage Model using modern SQLAlchemy 2.0 Mapping."""
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[str] = mapped_column(String(50), nullable=False)  # Format: "YYYY-MM-DD HH:MM"
    duration_minutes: Mapped[int] = mapped_column(default=60)

class ExpenseRecord(Base):
    """Persistent expense tracking with categories."""
    __tablename__ = "expense_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)

class UserPasscode(Base):
    """Stores bcrypt-hashed passcode for app authentication."""
    __tablename__ = "user_passcode"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    passcode_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)