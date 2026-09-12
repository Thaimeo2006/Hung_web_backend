"""Declare tables structure in sql database"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import secrets
from urllib.parse import quote_plus

with open("password/database_password.txt", "r") as f:
    mssql_password = f.read().strip()

DATABASE_URL = (
    f"mssql+pyodbc://sa:{quote_plus(mssql_password)}@127.0.0.1:1433/water_meter"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&TrustServerCertificate=yes"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    #id = Column(Integer, primary_key= True)
    id = Column(String(64), primary_key=True, default=lambda: secrets.token_hex(32))
    username = Column(String(32), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    records_taken = relationship("WaterRecord", back_populates="photographer")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(64), primary_key=True, nullable=False, default=lambda: secrets.token_hex(32))
    name = Column(String(40))
    identity_number = Column(String(12), nullable=False, unique=True)
    address = Column(String(120), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    last_paid_record_id = Column(
        Integer, 
        ForeignKey("water_records.id", use_alter=True, name="fk_customer_last_paid"), 
        nullable=True
    )

    records = relationship(
        "WaterRecord", 
        back_populates="customer", 
        foreign_keys="[WaterRecord.customer_id]"
    )

    last_paid_record = relationship(
        "WaterRecord", 
        foreign_keys=[last_paid_record_id],
        post_update=True # Must have to except error loops
    )

class WaterRecord(Base):
    __tablename__ = "water_records"

    id = Column(Integer, primary_key=True)
    customer_id = Column(String(64), ForeignKey("customers.id"), nullable= False)
    image_path = Column(String(256), nullable=False)
    record_time = Column(DateTime(timezone= True), server_default=func.sysdatetimeoffset(), nullable= False)
    result = Column(Float, nullable= False)
    ability = Column(Integer)
    coordinates_path = Column(String(256))
    photographer_id = Column(String(64), ForeignKey("users.id"), nullable=False)

    #Relationship
    customer = relationship("Customer", back_populates="records", foreign_keys=[customer_id])
    photographer = relationship("User", back_populates="records_taken", foreign_keys=[photographer_id])

Base.metadata.create_all(bind=engine)