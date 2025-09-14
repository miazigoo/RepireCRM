from ninja import Schema
from typing import Optional
from .common import UserSchema


class LoginSchema(Schema):
    username: str
    password: str


class TokenSchema(Schema):
    access_token: str
    token_type: str
    expires_in: int
    user: UserSchema


class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str
    confirm_password: str

    def validate(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        if len(self.new_password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")