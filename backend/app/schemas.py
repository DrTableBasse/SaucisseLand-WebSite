from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    discord_id: str
    username: str
    discriminator: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ArticleBase(BaseModel):
    title: str
    slug: Optional[str] = None
    content: str
    excerpt: Optional[str] = None
    published: bool = False

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    published: Optional[bool] = None

class ArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    published: bool
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: UserResponse
    
    class Config:
        from_attributes = True

class ArticleListResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    published: bool
    author: UserResponse
    created_at: datetime
    
    class Config:
        from_attributes = True

class ImageResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

