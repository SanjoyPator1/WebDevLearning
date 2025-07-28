from app.database.engine import get_database_session

# Use this as the FastAPI dependency
get_db = get_database_session