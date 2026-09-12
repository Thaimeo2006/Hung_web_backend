"""Main program, run the server, manage admin page, connect to mobile app"""

from database import SessionLocal, User, Customer, WaterRecord, engine
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Query, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func
#from sqlalchemy import text
from sqlalchemy.orm import Session
from sqladmin import Admin
from datetime import datetime, timezone, timedelta
from admin import authentication_backend, UserAdmin, CustomerAdmin, WaterRecordAdmin
from password_store import pwd_context
from starlette.background import BackgroundTasks
from uuid import uuid4
import tempfile
import os
import secrets
import zipfile
import csv
import io
import aiofiles
import jwt

try:
    with open("password/token_for_ai_dev.txt", "r") as f:
        AI_TOKEN = f.read().strip()
except FileNotFoundError:
    raise

try:
    with open("password/jwt_secret_key.txt", "r") as f:
        JWT_SECRET_KEY = f.read().strip()
except FileNotFoundError:
    raise

JWT_ALGORITHM = "HS256"
SESSION_TOKEN_EXPIRE_DAYS = 30
TIMEZONE_VIETNAM = 7

#Generate jwt token function
def create_session_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=SESSION_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

#Create "images" dir to save image
os.makedirs("./images", exist_ok=True)
#Create "coordinates" dir to save log file from AI model
os.makedirs("./coordinates", exist_ok=True)

security = HTTPBearer()

def check_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])        
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token payload invalid.")            
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def cleanup_temp_file(path: str):
    if os.path.exists(path):
        os.remove(path)

app = FastAPI()
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/coordinates", StaticFiles(directory="coordinates"), name="coordinates")

#Admin page initialize
admin = Admin(app, engine, authentication_backend=authentication_backend)

#Menu page for admin initialize
admin.add_view(UserAdmin)
admin.add_view(CustomerAdmin)
admin.add_view(WaterRecordAdmin)

@app.post("/login")
def check_login(
    username: str = Form(),
    password: str = Form(),
    db: Session = Depends(get_db)
):
    if username=="":
        return HTTPException(
            status_code= 400,
            detail= "Do not leave the username blank"
        )
    user_record = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )
    if user_record is not None:
        if pwd_context.verify(password, user_record.password_hash):
            session_token = create_session_token(data={"sub": str(user_record.id)})
            return {
                "message": "Logged in successfully! Send it to server for any request.",
                "user_id": user_record.id,
                "session_token": session_token,
            }
    return HTTPException(
        status_code= 400,
        detail= "Invalid username or password."
    )

@app.post("/logout")
def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    
    return {
        "message": "Logged out successfully! Delete session token on client side."
    }

@app.post("/check_and_save")
async def check_and_save(
    user_id: int = Depends(check_user),
    customer_id: str = Form(),
    image: UploadFile = File(),
    record_time: datetime = Form(),
    result: float = Form(),
    ability: int = Form(),
    coordinates: UploadFile = File(),
    db: Session = Depends(get_db)
):
    #Get latest record of customer
    latest_record = (
        db.query(WaterRecord)
        .filter(WaterRecord.customer_id == customer_id)
        .order_by(WaterRecord.record_time.desc())
        .first()
    )

    #Check new record
    if record_time.tzinfo is None:
        record_time = record_time.replace(tzinfo=timezone(timedelta(hours=TIMEZONE_VIETNAM)))
    record_time = record_time.astimezone(timezone.utc)
    if latest_record is not None:
        if result < latest_record.result:
            raise HTTPException(
                status_code= 400,
                detail= "The result result is less than the latest record result. Please try again"
            )
        #Maybe pyodbc return Naive Datetime
        db_time = latest_record.record_time
        if db_time.tzinfo is None:
           db_time = db_time.replace(tzinfo=timezone.utc)

        if record_time <= db_time:
            raise HTTPException(
                status_code= 400,
                detail= "Record time is older than the latest record time. Please try again."
            )

    # Save new record
    new_name = str(uuid4())

    image_relativepath = os.path.join("images", f"{new_name}.jpeg")
    coordinates_relativepath = os.path.join("coordinates", f"{new_name}.txt")

    try:
        async with aiofiles.open(image_relativepath, "wb") as buffer:
            while chunk := await image.read(1024 * 1024):
                await buffer.write(chunk)

        coordinates_data = await coordinates.read()
        async with aiofiles.open(coordinates_relativepath, "wb") as f:
            await f.write(coordinates_data)
    except Exception as e:
        if os.path.exists(image_relativepath):
            os.remove(image_relativepath)
        if os.path.exists(coordinates_relativepath):
            os.remove(coordinates_relativepath)

        raise HTTPException(
            status_code = 500,
            detail= f"Database error: {str(e)}"
        )

    try:
        new_record = WaterRecord(
            customer_id=customer_id,
            image_path=image_relativepath,
            record_time= record_time,
            result=result,
            ability= ability,
            coordinates_path= coordinates_relativepath,
            photographer_id= user_id
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
    except Exception as e:
        db.rollback()
        if image_relativepath and os.path.exists(image_relativepath):
            os.remove(image_relativepath)
        if coordinates_relativepath and os.path.exists(coordinates_relativepath):
            os.remove(coordinates_relativepath)
        raise HTTPException(
            status_code=500,
            detail=f"Add to sql database failed. {str(e)}"
        )

    return {
        "message": "Record saved!"
    }

@app.get("/history")
def serve_history_summary(
    user_id: str = Depends(check_user),
    customer_id: str = Query(...),
    limit: int = Query(20, description="Maximum return records"),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    try:
        records = (
            db.query(WaterRecord)
            .filter(WaterRecord.customer_id == customer_id)
            .order_by(WaterRecord.record_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        history_data = []
        for record in records:
            history_data.append({
                "id": record.id,
                "record_time": record.record_time,
                "result": record.result
            })

        return {
            "message": "Retrieved history successfully",
            "data": history_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/history/{record_id}")
def serve_history_detail(
    record_id: int,
    user_id: str = Depends(check_user),
    db: Session = Depends(get_db)
):
    try:
        record = db.query(WaterRecord).filter(WaterRecord.id == record_id).first()

        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {
            "message": "Retrieved detail of record successfully!",
            "data": {
                "id": record.id,
                "record_time": record.record_time,
                "image_url": f"/image/{record.id}",
                "result": record.result,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/image/{record_id}")
def serve_image(
    record_id: int,
    user_id: str = Depends(check_user),
    db: Session = Depends(get_db)
):
    try:
        record = db.query(WaterRecord).filter(WaterRecord.id == record_id).first()

        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")

        image_path = record.image_path
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file missing on server")
        return FileResponse(path=image_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/nearby_meter")
def serve_nearby_meters(
    user_id: str = Depends(check_user),
    limit: int = Query(default= 5),
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: Session = Depends(get_db)
):
    #Collect recorded customer today
    #Add timezone in config.json in the future
    timezone_vn = timezone(timedelta(hours=7))
    today_start = datetime.now(timezone_vn).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    recorded_customer = (
        db.query(WaterRecord.customer_id)
        .filter(WaterRecord.record_time >= today_start)
        .subquery()
    )
    
    #Spherical Law of Cosines Function (to M)
    lat_rad = func.radians(latitude)
    lon_rad = func.radians(longitude)

    db_lat_rad = func.radians(Customer.latitude)
    db_lon_rad = func.radians(Customer.longitude)
    
    distance_expr = 6371000.0 * func.acos(
        func.sin(lat_rad) * func.sin(db_lat_rad) +
        func.cos(lat_rad) * func.cos(db_lat_rad) * func.cos(db_lon_rad - lon_rad)
    )

    try:
        nearby_customers = (
            db.query(
                Customer.id,
                Customer.name,
                Customer.identity_number,
                Customer.address,
                #distance_expr.label("distance_m")
            )
            .filter(
                Customer.latitude.isnot(None),
                Customer.longitude.isnot(None),
                ~Customer.id.in_(recorded_customer)
                )
            .order_by(distance_expr.asc())
            .limit(limit)
            .all()
        )

        result = []
        for customer in nearby_customers:
            result.append({
                "id": customer.id,
                "name": customer.name,
                "identity_number": customer.identity_number,
                "address": customer.address
            })

        return {
            "message": "Retrieved nearby customers successfully!",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/new_customer")
def make_new_customer(
    user_id: str = Depends(check_user),
    name: str = Form(),
    identity_number: str = Form(),
    address: str = Form(),
    latitude: float = Form(),
    longitude: float = Form(),
    force_add: bool = Form(False, description="Force add the customer while maybe it existed"),
    db: Session = Depends(get_db)
):
    #Check existed customer with the same identity_number
    if not force_add:
        #Distance function
        lat_rad = func.radians(latitude)
        lon_rad = func.radians(longitude)
        db_lat_rad = func.radians(Customer.latitude)
        db_lon_rad = func.radians(Customer.longitude)
        
        distance_expr = 6371000.0 * func.acos(
            func.sin(lat_rad) * func.sin(db_lat_rad) +
            func.cos(lat_rad) * func.cos(db_lat_rad) * func.cos(db_lon_rad - lon_rad)
        )

        check_exist_customer = (
            db.query(Customer, distance_expr.label("distance_m"))
            .filter(Customer.identity_number == identity_number)
            .all()
        )
        
        if len(check_exist_customer) > 0:
            return_customer = []
            for row in check_exist_customer:
                customer, distance_m = row.Customer, row.distance_m
                distance_m = int(round(distance_m, 0))
                return_customer.append({
                    "name": customer.name,
                    "identity_number": customer.identity_number,
                    "address": customer.address,
                    "distance": distance_m
                })
            return {
                "message": f"Another customer with the same identity number already exists. Still save this new customer?",
                "exist_customer": return_customer
            }

    #Save to database
    try:
        new_customer = Customer(
            name=name,
            identity_number=identity_number,
            address=address,
            latitude=latitude,
            longitude=longitude
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        
        return {
            "message": "Add new customer successfully!",
            "customer_id": new_customer.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/export_record_data")
def export_ai_dataset(
    background_tasks: BackgroundTasks,
    ai_token: str = Header(..., description="Unique token for AI developer"),
    db: Session = Depends(get_db)
):
    #Check token
    if ai_token != AI_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    records = db.query(WaterRecord).all()
    fd, temp_zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)

    try:
        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)
            csv_writer.writerow(["record_id", "image_filename", "coordinates_filename", "ability"])

            for record in records:
                img_name = os.path.basename(record.image_path) if record.image_path else ""
                coord_name = os.path.basename(record.coordinates_path) if record.coordinates_path else ""

                if record.image_path and os.path.exists(record.image_path):
                    zip_file.write(record.image_path, arcname=f"images/{img_name}")

                if record.coordinates_path and os.path.exists(record.coordinates_path):
                    zip_file.write(record.coordinates_path, arcname=f"coordinates/{coord_name}")

                csv_writer.writerow([record.id, img_name, coord_name, record.ability])

            zip_file.writestr("dataset_labels.csv", csv_buffer.getvalue())

    except Exception as e:
        cleanup_temp_file(temp_zip_path)
        raise HTTPException(status_code=500, detail=f"Error in creating zip file: {str(e)}")

    background_tasks.add_task(cleanup_temp_file, temp_zip_path)
    
    return FileResponse(
        path=temp_zip_path, 
        filename="water_meter_dataset.zip", 
        media_type="application/zip"
    )