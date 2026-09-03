from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import secrets

with open("database_password.txt", "r") as f:
    mssql_password = f.read().strip("\n")

DATABASE_URL = (
    f"mssql+pyodbc://sa:{mssql_password}@localhost:1433/water_meter"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&TrustServerCertificate=yes"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    #id = Column(Integer, primary_key= True)
    id = Column(
        String(64),
        primary_key=True,
        default=lambda: secrets.token_hex(32)
    )
    email = Column(String(32), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    #Relationship with record table
    records = relationship("WaterRecord", back_populates="owner")

class WaterRecord(Base):
    __tablename__ = "water_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable= False)
    image_path = Column(String(256), nullable=False)
    record_time = Column(DateTime(timezone= True), server_default=func.sysdatetimeoffset(), nullable= False)
    result = Column(Float, nullable= False)
    ability = Column(Integer)
    coordinates_path = Column(String(256))

    #Relationship with users table
    owner = relationship("User", back_populates="records")

Base.metadata.create_all(bind=engine)