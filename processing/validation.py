from pydantic import BaseModel, field_validator
from datetime import datetime


class Measurement(BaseModel):
    timestamp: datetime
    name: str
    type: str
    temperature: float
    pressure: float
    x_deg: float 
    y_deg: float 
    z_km: float 

    @field_validator("temperature")
    def validate_temperature(cls, value):
        if value < -273:
            raise ValueError("Temperatur unter absolutem Nullpunkt")

        return value

    @field_validator("pressure")
    def validate_pressure(cls, value):
        if value <= 0:
            raise ValueError("Druck muss positiv sein")

        return value