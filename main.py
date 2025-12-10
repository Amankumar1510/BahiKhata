from fastapi import FastAPI
from sheets_service import GoogleSheetService
from goods_service import GoodsService
from payment_service import PaymentService
from customer_service import CustomerService

app = FastAPI()

sheet = GoogleSheetService("TransactionsData")

goods = GoodsService(sheet)
payments = PaymentService(sheet)
customers = CustomerService(sheet)


@app.post("/customer/add")
def add_customer(name: str, phone: str = "", notes: str = ""):
    return customers.add_customer(name, phone, notes)


@app.post("/goods/add")
def add_goods(customer_id: int, units: int, weight: float, price_per_kg: float):
    return goods.add_goods_sold(customer_id, units, weight, price_per_kg)


@app.post("/payment/add")
def add_payment(customer_id: int, amount: float, payment_mode: str):
    return payments.add_payment(customer_id, amount, payment_mode)
