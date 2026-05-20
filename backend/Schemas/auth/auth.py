from ninja import Schema
from pydantic import model_validator

from Schemas.common import UserSchema


class LoginSchema(Schema):
    username: str
    password: str

    @model_validator(mode="after")
    def strip_surrounding_whitespace(self) -> "LoginSchema":
        self.username = self.username.strip()
        self.password = self.password.strip()
        return self


class TokenSchema(Schema):
    access_token: str
    token_type: str
    expires_in: int
    user: UserSchema


class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordSchema":
        if self.new_password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        if len(self.new_password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        return self
