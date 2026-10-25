import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

_DISPLAY_NAME = re.compile(r"^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$")


def clean_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(value.split())
    if not collapsed:
        return None
    if (
        "@" in collapsed
        or _DISPLAY_NAME.fullmatch(collapsed) is None
        or not 2 <= len(collapsed) <= 32
    ):
        raise ValueError("Use 2–32 letters, numbers, and single spaces")
    return collapsed


class PreferencesRead(BaseModel):
    theme: Literal["dark", "light"] = "dark"


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    theme: Literal["dark", "light"] | None = None
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def _display_name(cls, value: str | None) -> str | None:
        return clean_display_name(value)


class DeleteAccount(BaseModel):
    password: str = Field(min_length=1, max_length=128)
