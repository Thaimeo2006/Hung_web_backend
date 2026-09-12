"""Define UI of admin page"""

from database import User, Customer, WaterRecord
from sqladmin import ModelView
from wtforms import Form, StringField, PasswordField
from wtforms.validators import DataRequired, Optional, Regexp, Length
from password_store import pwd_context
from markupsafe import Markup

class UserForm(Form):

    username = StringField(
        "Username",
        validators=[
            DataRequired()
        ]
    )

    password = PasswordField(
        "New password",
        validators=[
            Optional(),
            Length(
                min=12,
                message="Password must be at least 12 characters."
            ),
            Regexp(
                r'^[\x21-\x7E]+$',
                message="Password contains invalid characters."
            )
        ]
    )

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username]
    column_searchable_list = [User.username]
    name = "Employee" 
    name_plural = "Employee list"
    icon = "fa-solid fa-user"

    column_details_list = [
        User.username,
        User.password_hash
    ]

    form = UserForm

    form_columns = [User.username, "password"]

    async def on_model_change(self, data, model, is_created, request):
        plain_password = data.pop("password", None)

        if is_created and not plain_password:
            raise ValueError("Password is required when creating a new employee!")

        if plain_password:
            data["password_hash"] = pwd_context.hash(plain_password)

class CustomerAdmin(ModelView, model=Customer):
    column_list = [Customer.id, Customer.name, Customer.identity_number, Customer.address]
    column_searchable_list = [Customer.name, Customer.identity_number]
    name = "Customer"
    name_plural = "Customer list"
    icon = "fa-solid fa-house"

    column_details_list = [
        Customer.name, 
        Customer.identity_number, 
        Customer.address,
        Customer.latitude,
        Customer.longitude,
        Customer.last_paid_record 
    ]

class WaterRecordAdmin(ModelView, model=WaterRecord):
    column_list = [
        WaterRecord.id,
        WaterRecord.customer_id,
        WaterRecord.photographer_id,
        WaterRecord.result,
        WaterRecord.record_time
    ]
    column_details_list = [
        WaterRecord.customer,
        WaterRecord.image_path,
        WaterRecord.result, 
        WaterRecord.record_time,
        WaterRecord.photographer,
        WaterRecord.coordinates_path,
        WaterRecord.ability
    ]
    column_labels = {
        WaterRecord.image_path: "image",
        WaterRecord.coordinates_path: "coordinates"
    }
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