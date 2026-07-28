import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import (
    auth,
    daily_summaries,
    machines,
    products,
    simulation,
    transactions,
)
from .services.scheduler_service import (
    create_scheduler,
    run_startup_maintenance,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(run_startup_maintenance)
    scheduler = create_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

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
app.include_router(simulation.router)
app.include_router(daily_summaries.router)
