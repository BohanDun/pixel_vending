from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, machines, products, transactions

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get("/")
def health_check():
    return "Health check complete"

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(machines.router)
app.include_router(transactions.router)
