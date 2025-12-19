from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from datetime import datetime,timezone
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TimeInput(BaseModel):
    source_city: str = ""
    dest_city: str = ""
    date_time_str: str = ""


geolocator = Nominatim(user_agent="time_tool")
tf = TimezoneFinder()

def _system_tzinfo():
    tz = datetime.now().astimezone().tzinfo
    return tz if tz else timezone.utc

def city_to_timezone(city):
    loc = geolocator.geocode(city, exactly_one=True)
    if not loc:
        raise ValueError(f"City not found: {city}")
    tz = tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
    if not tz:
        raise ValueError(f"Timezone not found for: {city}")
    return tz

def convert_time(source_city: str, dest_city: str, date_time_str: str | None):
    # UI can enforce this too, but backend should still guard it.
    if not dest_city or not dest_city.strip():
        raise ValueError("Destination city cannot be empty")

    source_city = (source_city or "").strip()
    dest_city = dest_city.strip()
    date_time_str = (date_time_str or "").strip()

    dst_tz = city_to_timezone(dest_city)  # returns IANA tz string like "Europe/London"
    dst_zone = ZoneInfo(dst_tz)

    # Case: Source empty + Time empty -> use system time, show in destination
    if not source_city and not date_time_str:
        return datetime.now(_system_tzinfo()).astimezone(dst_zone)

    # Optional safety: Source empty + Time given -> treat given time as system-local time
    if not source_city and date_time_str:
        src_time = datetime.fromisoformat(date_time_str).replace(tzinfo=_system_tzinfo())
        return src_time.astimezone(dst_zone)

    # Source given (time given or empty)
    src_tz = city_to_timezone(source_city)
    src_zone = ZoneInfo(src_tz)
    if len(date_time_str) == 5:  # "HH:MM"
      date_time_str = datetime.now().date().isoformat() + " " + date_time_str

    if date_time_str:
        src_time = datetime.fromisoformat(date_time_str).replace(tzinfo=src_zone)
    else:
        # Case: Source given + Time empty -> current time in source, convert to destination
        src_time = datetime.now(src_zone)

    # Case: Source given + Destination given + Time given -> normal convert
    return src_time.astimezone(dst_zone)




@app.get("/")
def home():
    return {"status": "ok"}

# @app.post("/convert")
# def convert_api(data: TimeInput):
#     result = convert_time(
#         data.source_city,
#         data.dest_city,
#         data.date_time_str
#     )
#     return {"result": result.strftime("%Y-%m-%d %H:%M")}

@app.post("/convert")
def convert_api(data: TimeInput):
    try:
        result = convert_time(data.source_city, data.dest_city, data.date_time_str)
        return {"result": result.strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


