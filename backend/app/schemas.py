from typing import Literal, Optional
from pydantic import BaseModel, Field
from .config import RATES
PH = r"^\d{10}$"; CODE = r"^\d{6}$"
class OtpReq(BaseModel): phone: str = Field(pattern=PH)
class Reg(BaseModel):
    phone: str = Field(pattern=PH); name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=8, max_length=100); role: Literal["collector", "recycler"]; code: str = Field(pattern=CODE)
class Login(BaseModel): phone: str = Field(max_length=15); password: str = Field(max_length=100)
class LoginOtp(BaseModel): phone: str = Field(pattern=PH); code: str = Field(pattern=CODE)
class LotIn(BaseModel):
    type: Literal[tuple(RATES)]; kg: float = Field(gt=0, le=5000); city: str = Field(min_length=2, max_length=60)
    lat: Optional[float] = Field(None, ge=-90, le=90); lng: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=200)
    pickup_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$"); pickup_slot: Optional[Literal["morning", "afternoon", "evening"]] = None
class LotEdit(BaseModel):
    kg: Optional[float] = Field(None, gt=0, le=5000); city: Optional[str] = Field(None, min_length=2, max_length=60)
    lat: Optional[float] = Field(None, ge=-90, le=90); lng: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=200)
    pickup_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$"); pickup_slot: Optional[Literal["morning", "afternoon", "evening"]] = None
class ChangePw(BaseModel): current: str = Field(max_length=100); new: str = Field(min_length=8, max_length=100)
class ResetPw(BaseModel): phone: str = Field(pattern=PH); code: str = Field(pattern=CODE); new: str = Field(min_length=8, max_length=100)
class StageIn(BaseModel): stage: Literal["on_the_way", "picked_up"]
class PayIn(BaseModel): method: Literal["cash", "upi"]; ref: Optional[str] = Field(None, max_length=40)
class BidIn(BaseModel): amount: float = Field(gt=0, le=10_000_000)
class RateIn(BaseModel): stars: int = Field(ge=1, le=5); comment: str = Field("", max_length=200)
class MsgIn(BaseModel): peer: str = Field(max_length=32); text: str = Field(min_length=1, max_length=500)
