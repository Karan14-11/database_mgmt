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