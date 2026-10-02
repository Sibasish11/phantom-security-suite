from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthenticatedUserResponse(BaseModel):
    user_id: str
    organization_id: str
    email: EmailStr
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthenticatedUserResponse
    organization_name: str | None = None


class CompanyRegistrationRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CompanyRegistrationResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthenticatedUserResponse
    organization_name: str
    organization_slug: str