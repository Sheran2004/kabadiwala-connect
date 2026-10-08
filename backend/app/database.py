from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DATABASE_URL
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
class Base(DeclarativeBase): pass
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def migrate():
    """Adds columns that newer versions need to tables created by older versions (keeps your data)."""
    insp = inspect(engine)
    with engine.begin() as c:
        for t in Base.metadata.sorted_tables:
            if not insp.has_table(t.name): continue
            have = {x["name"] for x in insp.get_columns(t.name)}
            for col in t.columns:
                if col.name in have: continue
                d = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    v = col.default.arg; d = " DEFAULT " + ("TRUE" if v is True else "FALSE" if v is False else repr(v))
                c.execute(text(f"ALTER TABLE {t.name} ADD COLUMN {col.name} {col.type.compile(engine.dialect)}{d}"))
