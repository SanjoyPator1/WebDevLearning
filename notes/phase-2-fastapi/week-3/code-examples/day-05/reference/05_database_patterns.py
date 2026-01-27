from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# --- SQLAlchemy Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- 1. Basic Session Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. Transaction Dependency (Commit/Rollback) ---
def get_db_transaction():
    db = SessionLocal()
    try:
        yield db
        db.commit() # Commit on success
    except Exception:
        db.rollback() # Rollback on error
        raise
    finally:
        db.close()

# --- 3. Repository Pattern ---
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str):
        return self.db.query(UserDB).filter(UserDB.name == name).first()

    def create(self, name: str):
        user = UserDB(name=name)
        self.db.add(user)
        # Note: No commit here if using get_db_transaction, 
        # or commit here if using plain get_db
        self.db.flush() 
        return user

def get_user_repo(db: Session = Depends(get_db_transaction)):
    return UserRepository(db)

# --- Endpoint ---
@app.post("/users/{name}")
async def create_user(name: str, repo: UserRepository = Depends(get_user_repo)):
    existing = repo.get_by_name(name)
    if existing:
        raise HTTPException(400, "User exists")
    repo.create(name)
    return {"status": "User created", "name": name}