from database import SessionLocal, User, WaterRecord
from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text, DateTime
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import tempfile
import os

#Create "uploads" dir to save image
os.makedirs("./uploads", exist_ok=True)
#Create "coordinates" dir to save log file from AI model
os.makedirs("./coordinates", exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
sessions={}
@app.get("/login")
def check_login():
    return FileResponse("login.html")

@app.post("/check_and_save")
async def check_and_save(
    user_id: str = Form(),
    session_token: str = Form(),
    image: UploadFile = File(),
    record_time: datetime = Form(),
    result: float = Form(),
    ability: int = Form(),
    coordinates: UploadFile = File(),
    db: Session = Depends(get_db)
):
    #Check user in sessions
    #if session_token not in sessions:
    #    raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    #if sessions[session_token] != user_id:
    #    raise HTTPException(status_code=403, detail="Unauthorized access for this user")

    #Get latest record of user
    latest_record = (
        db.query(WaterRecord)
        .filter(WaterRecord.user_id == user_id)
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
        if record_time <= latest_record.record_time:
            raise HTTPException(
                status_code= 400,
                detail= "Record time is older than the latest record time. Please try again."
            )

    #Maybe podbc return Naive Datetime
        db_time = latest_record.record_time
        if db_time.tzinfo is None:
            db_time = db_time.replace(tzinfo=timezone.utc)

    # Save new record
    try:
        with tempfile.NamedTemporaryFile(
            dir= "./uploads",
            suffix= ".jpeg",
            mode= "wb",
            delete= False
        ) as image_file:
            image_file.write(await image.read())
            image_filename = os.path.basename(image_file.name)
        image_relativepath = os.path.join("uploads", image_filename)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail= f"Make new image file failed. {str(e)}"
        )

    with tempfile.NamedTemporaryFile(
        dir= "./coordinates",
        suffix= ".txt",
        mode= "w",
        delete= False
    ) as coordinates_file:
        coordinates_file.write(coordinates.read())
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
    user_id: int = Query(...), 
    session_token: str = Query(...),
    limit: int = Query(20, description="Số lượng bản ghi tối đa trả về"),
    offset: int = Query(0, description="Vị trí bắt đầu lấy (dùng để chuyển trang)"),
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra xác thực user
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    if sessions[session_token] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access for this user")

    # 2. Truy vấn Database lấy danh sách
    try:
        records = (
            db.query(WaterRecord)
            .filter(WaterRecord.user_id == user_id)
            .order_by(WaterRecord.record_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # 3. Format lại dữ liệu trả về (CHỈ LẤY THÔNG TIN TÓM TẮT)
        history_data = []
        for r in records:
            history_data.append({
                "id": r.id,
                "predicted": r.predicted,
                "record_time": r.record_time
                # KHÔNG gửi kèm image_path hay image_url ở đây
            })

        return {
            "status": "success",
            "total_returned": len(history_data),
            "data": history_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")