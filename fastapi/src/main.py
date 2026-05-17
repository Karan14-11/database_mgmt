from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models, schemas, tasks
from .database import engine, get_db, Base

# Create tables automatically (in a real app, use Alembic for migrations!)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flash Sale Fulfillment API")

# Seed a test book when the app starts
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    if not db.query(models.Book).first():
        book = models.Book(title="System Design Guide", stock=100)
        db.add(book)
        db.commit()

@app.post("/orders", response_model=schemas.OrderResponse, status_code=202)
def place_order(order_req: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Places an order safely using database row-level locking."""
    
    # BEGIN TRANSACTION with a Row Lock (FOR UPDATE)
    book = db.query(models.Book).filter(models.Book.id == order_req.book_id).with_for_update().first()
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    if book.stock < order_req.quantity:
        raise HTTPException(status_code=400, detail="Out of stock!")
        
    # Deduct stock and create order
    book.stock -= order_req.quantity
    new_order = models.Order(book_id=order_req.book_id, quantity=order_req.quantity, status="pending")
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Fire off the asynchronous background task to Celery
    tasks.process_fulfillment.delay(new_order.id)
    
    return new_order

@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
def get_order_status(order_id: int, db: Session = Depends(get_db)):
    """Allows users to poll their order status."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order



@app.post("/books", response_model=schemas.BookResponse, status_code=202)
def add_book(order_req:schemas.BookAdd , db: Session = Depends(get_db)):
    
    book = db.query(models.Book).filter(models.Book.title == order_req.title).first()

    if book:
        raise HTTPException(status_code = 400, detail ="Book already exists")
    
    book = models.Book(title=order_req.title, stock=order_req.quantity)
    db.add(book)
    db.commit()
    db.refresh(book)

    return book

    


