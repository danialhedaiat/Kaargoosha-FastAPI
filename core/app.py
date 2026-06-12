from contextlib import asynccontextmanager

from fastapi import FastAPI


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