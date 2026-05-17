from pydantic import BaseModel

class OrderCreate(BaseModel):
    book_id: int
    quantity: int

class OrderResponse(BaseModel):
    id: int
    book_id: int
    quantity: int
    status: str

    class Config:
        from_attributes = True

class BookAdd(BaseModel):
    title: str
    quantity: int

class BookResponse(BaseModel):
    id: int
    title: str
    stock: int

    class Config:
        from_attributes = True
