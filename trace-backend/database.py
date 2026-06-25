import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load environment variables from .env file if it exists, otherwise bootstrap from .env.example
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
env_example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")

if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()
elif os.path.exists(env_example_path):
    try:
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    except Exception as e:
        print(f"Warning: Could not bootstrap .env from .env.example: {e}")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./trace.db"
)

DATABASE_REPLICA_URL = os.getenv("DATABASE_REPLICA_URL")

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False
}

# 1. PostgreSQL (production) pooling and SSL settings
if DATABASE_URL.startswith(("postgresql", "postgres")):
    connect_args["sslmode"] = "require"
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_recycle": 1800
    })
elif DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Try utilizing sqlite+pysqlcipher dialect if DB_ENCRYPTION_KEY is provided
# and falls back gracefully to standard sqlite if pysqlcipher3 isn't compiled.
if DATABASE_URL.startswith("sqlite+pysqlcipher"):
    try:
        import pysqlcipher3
    except ImportError:
        print("Warning: pysqlcipher3 is not installed. Falling back to standard sqlite dialect.")
        DATABASE_URL = DATABASE_URL.replace("sqlite+pysqlcipher", "sqlite")

# Create Main Database Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# 2. SQLite Pragma listener: enforce WAL mode, Synchronous=FULL, Foreign Keys, and key verification
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=FULL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        # Apply SQLCipher encryption password if set
        db_key = os.getenv("DB_ENCRYPTION_KEY")
        if db_key:
            try:
                cursor.execute(f"PRAGMA key = '{db_key}';")
            except Exception as e:
                print(f"Warning: Could not apply SQLCipher key: {e}")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Read Replica Configuration ──────────────────────────────────────────────────

replica_engine = None
ReplicaSessionLocal = SessionLocal

if DATABASE_REPLICA_URL:
    replica_kwargs = engine_kwargs.copy()
    replica_connect_args = connect_args.copy()
    
    if DATABASE_REPLICA_URL.startswith("sqlite+pysqlcipher"):
        try:
            import pysqlcipher3
        except ImportError:
            DATABASE_REPLICA_URL = DATABASE_REPLICA_URL.replace("sqlite+pysqlcipher", "sqlite")
            
    replica_engine = create_engine(
        DATABASE_REPLICA_URL,
        connect_args=replica_connect_args,
        **replica_kwargs
    )
    
    if DATABASE_REPLICA_URL.startswith("sqlite"):
        @event.listens_for(replica_engine, "connect")
        def set_replica_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=FULL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            db_key = os.getenv("DB_ENCRYPTION_KEY")
            if db_key:
                try:
                    cursor.execute(f"PRAGMA key = '{db_key}';")
                except Exception:
                    pass
            cursor.close()
            
    ReplicaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=replica_engine)


class Base(DeclarativeBase):
    pass


# ── Database Dependencies ──────────────────────────────────────────────────────

def get_db():
    """Returns database session wrapper for write transactions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    """Returns read-only database session wrapper (points to read replica if active)"""
    db = ReplicaSessionLocal()
    try:
        yield db
    finally:
        db.close()
