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


class Metadata(SQLModel, table=True):
    id: str = Field(primary_key=True)
    filename: str
    author: str
    language: str
    date_added: datetime
    size: int
    file_type: str
    source_filename: str
    pages: int
    status: int
    s3_key: str

db_uri = MySQLDsn.build(
    scheme="mysql+pymysql", # MySQL driver
    username=db_user,
    password=db_password,
    host=db_host,
    port=3306,
    path=db_name  # Important: Include '/' before DB name
)

engine = create_engine(str(db_uri))
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    meta = Metadata(
        id="def456",
        filename="newfile.pdf",
        author="Bob",
        language="en",
        date_added=datetime.now(),
        size=204800,
        file_type="pdf",
        source_filename="original_newfile.pdf",
        pages=5,
        status=1,
        s3_key="def456/newfile.pdf"
    )
    session.add(meta)
    session.commit()

    # Query
    statement = select(Metadata).where(Metadata.id == "def456")
    result = session.exec(statement).first()
    print(result)

