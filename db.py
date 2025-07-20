import os
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import quote_plus
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import MySQLDsn

load_dotenv()

db_host = os.getenv("MYSQL_HOST")
db_port = os.getenv("MYSQL_PORT")
db_user = os.getenv("MYSQL_USER")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DB_NAME")

db_uri = MySQLDsn.build(
    scheme="mysql+pymysql", # MySQL driver
    username=db_user,
    password=db_password,
    host=db_host,
    port=3306,
    path=db_name  # Important: Include '/' before DB name
)

class DatabaseManager:
    def __init__(self):
        self.engine = None
    
    def init_db(self, db_uri: str):
        self.engine = create_engine(db_uri, pool_size=20) # at most 20 db connections
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        return Session(self.engine)

# Global instance
db_manager = DatabaseManager()

def get_db():
    with db_manager.get_session() as session:
        try:
            yield session
        finally:
            session.close()

# DB connections = tunnels
# sessions = workers
# workers deliver data to DB through tunnels