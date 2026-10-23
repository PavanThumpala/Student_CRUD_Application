from datetime import date
from pydantic import BaseModel, EmailStr, Field, model_validator


class StudentCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    course: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Provide an email address or phone number.")
        return self
class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    course: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None
