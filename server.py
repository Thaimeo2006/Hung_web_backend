from database import SessionLocal, User, WaterRecord
from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
#from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from passlib.context import CryptContext
import tempfile
import os
import secrets

#Create "images" dir to save image
os.makedirs("./images", exist_ok=True)
#Create "coordinates" dir to save log file from AI model
os.makedirs("./coordinates", exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

app = FastAPI()
sessions={}

def garbage_collector():
    pass

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
            session_token = secrets.token_hex(32)
            sessions["session_token"] = user_record.id
            return {
                "message": "Login successful",
                "user_id": user_record.id,
                "session_token": session_token,
            }
    return HTTPException(
        status_code= 400,
        detail= "Invalid username or password"
    )

@app.post("/check_and_save")
async def check_and_save(
    session_token: str = Form(),
    customer_id: str = Form(),
    image: UploadFile = File(),
    record_time: datetime = Form(),
    result: float = Form(),
    ability: int = Form(),
    coordinates: UploadFile = File(),
    db: Session = Depends(get_db)
):
    #Verify user
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    user_id = sessions["session_token"]

    #Get latest record of user
    latest_record = (
        db.query(WaterRecord)
        .filter(WaterRecord.customer_id == customer_id)
        .order_by(WaterRecord.record_time.desc())
        .first()
    )

    #Check new record
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
    try:
        with tempfile.NamedTemporaryFile(
            dir= "./images",
            suffix= ".jpeg",
            mode= "wb",
            delete= False
        ) as image_file:
            image_data = await image.read()
            image_file.write(image_data)
            image_filename = os.path.basename(image_file.name)
        image_relativepath = os.path.join("images", image_filename)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail= f"Make new image file failed. {str(e)}"
        )

    with tempfile.NamedTemporaryFile(
        dir= "./coordinates",
        suffix= ".txt",
        mode= "wb",
        delete= False
    ) as coordinates_file:
        coordinates_data = await coordinates.read()
        coordinates_file.write(coordinates_data)
        coordinates_filename = os.path.basename(coordinates_file.name)
    coordinates_relativepath = os.path.join("coordinates", coordinates_filename)

    try:
        new_record = WaterRecord(
            user_id=user_id,
            image_path=image_relativepath,
            record_time= record_time,
            result=result,
            ability= ability,
            coordinates_path= coordinates_relativepath
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        return {
            "status": "success", 
            "message": "Record saved.", 
            #"record_id": new_record.id
        }
    except Exception as e:
        db.rollback()
        if os.path.exists(image_file.name):
            os.remove(image_file.name)
        if os.path.exists(coordinates_file.name):
            os.remove(coordinates_file.name)
        raise HTTPException(
            status_code=500,
            detail=f"Add to sql database failed. {str(e)}"
        )

@app.get("/history")
def serve_history_summary(
    user_id: str = Query(...), 
    session_token: str = Query(...),
    limit: int = Query(20, description="Maximum return records"),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    #Check user in sessions
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    user_id = sessions["session_token"]

    try:
        records = (
            db.query(WaterRecord)
            .filter(WaterRecord.user_id == user_id)
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
            "status": "success",
            "total_returned": len(history_data),
            "data": history_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/history/{record_id}")
def serve_history_detail(
    record_id: int,
    user_id: str = Query(...),
    session_token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Check user in sessions
    # if session_token not in sessions:
    #     raise HTTPException(status_code=401, detail="Session invalid or expired")
    # if sessions[session_token] != user_id:
    #     raise HTTPException(status_code=403, detail="Unauthorized access for this user")

    try:
        record = db.query(WaterRecord).filter(WaterRecord.id == record_id).first()

        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to view this record")

        return {
            "status": "success",
            "data": {
                "id": record.id,
                "record_time": record.record_time,
                "image_url": f"/image/{record.id}?user_id={user_id}&session_token={session_token}",
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
    user_id: str = Query(...), 
    session_token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Check user in sessions
    # if session_token not in sessions:
    #     raise HTTPException(status_code=401, detail="Session invalid or expired")
    # if sessions[session_token] != user_id:
    #     raise HTTPException(status_code=403, detail="Unauthorized access for this user")

    try:
        record = db.query(WaterRecord).filter(WaterRecord.id == record_id).first()

        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        image_path = record.image_path
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file missing on server")
        return FileResponse(path=image_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")