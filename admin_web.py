from fastapi import FastAPI, Form, HTTPException, Request, File, UploadFile, Depends
from fastapi.responses import FileResponse, RedirectResponse
from passlib.context import CryptContext
from database import SessionLocal, User, WaterRecord
from sqlalchemy import text
import secrets
import json
import tempfile

sessions = []

with open("admin_account.json", "r") as f:
    admin_account = json.load(f)
    admin_username, admin_password_hash = admin_account["username"], admin_account["password_hash"]

#Check admin for any request
def check_admin(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    if session_id not in sessions:
        raise HTTPException(
            status_code= 401,
            detail= "Unknown session id"
        )

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

sessions={}

app = FastAPI(title="For administrator")

@app.get("/")
async def serve_main_page(request: Request):
    try:
        check_admin(request)
    except HTTPException:
        return RedirectResponse("/login")
    return FileResponse("main_page.html")

@app.get("/login")
async def serve_login_form():
    return FileResponse("login.html")

@app.post("/login")
async def check_login_form(
    username: str = Form(),
    password: str = Form()
):
    if username != admin_username:
        raise HTTPException(
            status_code = 400,
            detail = "Only admin can login"
        )
    if pwd_context.verify(password, admin_password_hash):
        raise HTTPException(
            status_code= 400,
            detail= "Invalid admin password."
        )

@app.get("/logout")
def logout_user():
    pass

@app.get("/users")
def serve_users_table():
    pass