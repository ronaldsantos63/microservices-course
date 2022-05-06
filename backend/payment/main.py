from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
import requests, time

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# This should be a different database
redis = get_redis_connection(
    host="redis-18585.c11.us-east-1-3.ec2.cloud.redislabs.com",
    port="18585",
    password="Dq4sMNgfEmEAyBTVoyQRsB4GYRF9MTlr",
    decode_responses=True
)

class Order(HashModel):
    product_id: str
    price: float
    quantity: int
    fee: float
    total: float
    status: str # pending, completed, refunded
    
    class Meta:
        database = redis
        
@app.get('/orders/{pk}')
def get(pk: str):
    return Order.get(pk)

@app.get('/orders')
def all():
    def format(pk):
        return Order.get(pk)
    return [format(pk) for pk in Order.all_pks()]

@app.post('/orders')
async def create(request: Request, background_tasks: BackgroundTasks): # id, quantity
    body = await request.json()
    
    req = requests.get(f'http://localhost:8000/products/{body["id"]}')
    product = req.json()
    
    order = Order(
        product_id=body['id'],
        price=product['price'],
        fee= 0.2 * product['price'],
        total=1.2 * product['price'],
        quantity=body['quantity'],
        status='pending'
    )
    order.save()
    background_tasks.add_task(order_completed, order)
    return order

def order_completed(order: Order):
    time.sleep(5)
    order.status = 'completed'
    order.save()
    redis.xadd('order_completed', order.dict(), '*')
