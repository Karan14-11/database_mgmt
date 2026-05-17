import os
import time
from celery import Celery
from .database import SessionLocal
from .models import Order

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(__name__, broker=CELERY_BROKER_URL)

@celery_app.task
def process_fulfillment(order_id: int):
    """
    Simulates a heavy background task like generating a PDF receipt 
    and sending an email, then updates the order status.
    """
    print(f"📦 Starting fulfillment for Order {order_id}...")
    
    time.sleep(5) 

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = "completed"
            db.commit()
            print(f"✅ Order {order_id} fulfillment complete!")
    finally:
        db.close()