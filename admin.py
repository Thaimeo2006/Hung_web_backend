from database import User, Customer, WaterRecord
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import Request
from password_store import pwd_context
from markupsafe import Markup
import secrets
import json

with open("admin_account.json", "r") as f:
    admin_account = json.load(f)
    admin_username, admin_password_hash = admin_account["username"], admin_account["password_hash"]

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == admin_username and pwd_context.verify(password, admin_password_hash):
            request.session.update({"session_token": secrets.token_hex(32)})
            return True            
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("session_token")
        if not token:
            return False
        return True

authentication_backend = AdminAuth(secret_key=secrets.token_hex(32))

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username]
    column_searchable_list = [User.username]
    name = "Employee" 
    name_plural = "Employee list"
    icon = "fa-solid fa-user"

class CustomerAdmin(ModelView, model=Customer):
    column_list = [Customer.id, Customer.name, Customer.identity_number, Customer.address]
    column_searchable_list = [Customer.name, Customer.identity_number]
    name = "Customer"
    name_plural = "Customer list"
    icon = "fa-solid fa-house"

class WaterRecordAdmin(ModelView, model=WaterRecord):
    column_list = [
        WaterRecord.id,
        WaterRecord.customer_id,
        WaterRecord.photographer_id,
        WaterRecord.result,
        WaterRecord.record_time
    ]
    column_details_list = [
        WaterRecord.id, 
        WaterRecord.customer,
        WaterRecord.image_path,
        WaterRecord.result, 
        WaterRecord.record_time,
        WaterRecord.photographer,
        WaterRecord.coordinates_path,
        WaterRecord.ability
    ]
    column_formatters_detail = {
        WaterRecord.image_path: lambda model, attribute: Markup(
            f'<a href="/{model.image_path}" target="_blank">'
            f'<img src="/{model.image_path}" style="max-height: 300px; border-radius: 8px; border: 1px solid #ccc; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">'
            f'</a>'
        ) if model.image_path else "",
        
        WaterRecord.coordinates_path: lambda model, attribute: Markup(
            f'<a href="/{model.coordinates_path}" target="_blank" style="padding: 8px 16px; background-color: #0d6efd; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">'
            f'<i class="fa-solid fa-file-lines"></i> See .txt file'
            f'</a>'
        ) if model.coordinates_path else ""
    }
    column_sortable_list = [WaterRecord.record_time, WaterRecord.result]
    column_default_sort = ("record_time", True) 
    name = "Water record"
    name_plural = "Water record list"
    icon = "fa-solid fa-droplet"