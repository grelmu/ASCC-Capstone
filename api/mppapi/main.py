import os
from fastapi import FastAPI
import motor.motor_asyncio

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/version")
async def version():
    return {"version": app.version}

if 'MONGODB_URL' in os.environ:

    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"],
                                                    username=os.environ["MONGODB_USERNAME"],
                                                    password=os.environ["MONGODB_PASSWORD"])

    @app.get("/server_info")
    async def version():
        return {"server_info": await client.server_info()}