import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("Application startup")
    yield
    print("Application shutdown")

app = FastAPI(
    title="Kaargoosha Emam Reza Investment",
    lifespan=lifespan,
    version="1.0.0",
    contact={
        "name": "Danial Hadi",
        "email": "danialhedaiat@gmail.com",
        "phone_number": "+989308222060"
    }
)

# Serve persisted receipt proofs so they are retrievable from any platform.
# NOTE: this mount is currently unauthenticated — gate it before production.
os.makedirs(os.path.join(settings.MEDIA_ROOT, "receipts"), exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")