"""Packages for NORAD-25544"""

from typing import Optional
import time
import json
import concurrent.futures
import uuid
import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn


# Data handling for NORAD-25544
load_dotenv()
def orbit() -> dict:
    """Get NORAD-25544 position and velocity from orbital arc"""
    axis = os.environ.get("axis")
    data = requests.get(axis, timeout=10)
    return data.json()


def surface(latitude: float, longitude: float) -> bool:
    """Check if ISS is above water"""
    blackbox = os.environ.get("blackbox")
    geocode = f'{os.environ.get("geocode")}?q={latitude}+{longitude}&key={blackbox}'
    response = requests.get(geocode, timeout=10).json()
    is_water = response['results'][0]['components']['_category']
    return is_water == 'natural/water'


# Main NORAD-25544 Data Stream API
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/v1/geolocation')
async def geolocation():
    """Get geodata for ISS"""
    geodata = orbit()
    print(geodata)
    geodata['above_water'] = surface(
        geodata['latitude'], geodata['longitude'])
    return JSONResponse(content=geodata)


@app.get('/v1/position')
async def position(request: Request, dealy: Optional[int] = 1):
    """Get position for ISS"""
    async def generator() -> dict:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            while True:

                if await request.is_disconnected():
                    break

                future = executor.submit(orbit)
                result = json.dumps(future.result())

                yield {
                    "id": uuid.uuid4().hex,
                    "retry": 1500,
                    "data": result
                }

                time.sleep(dealy)

    return EventSourceResponse(generator())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=25544)
