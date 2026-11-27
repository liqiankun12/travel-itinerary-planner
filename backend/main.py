import json
import sqlite3
from datetime import date
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()
DB = Path(__file__).with_name("travel.db")
class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    conn = sqlite3.connect(DB, factory=ClosingConnection)
    conn.execute("CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)")
    return conn

class CreateTrip(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    startDate: date
    dayCount: int = Field(ge=2, le=5, strict=True)
    budgetLimitCents: int = Field(ge=0, le=100000000, strict=True)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("名称不能为空")
        return value

class Item(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    attractionId: str = Field(min_length=1)
    order: int = Field(ge=0, strict=True)
    durationMinutes: int = Field(ge=1, le=720, strict=True)

class Expense(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    amountCents: int = Field(ge=0, le=100000000, strict=True)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("费用名称不能为空")
        return value.strip()

class DayPlan(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    dayIndex: int = Field(ge=1, le=5, strict=True)
    startMinutes: int = Field(ge=0, lt=1440, strict=True)
    endMinutes: int = Field(gt=0, le=1440, strict=True)
    items: list[Item] = Field(default_factory=list, max_length=20)
    expenses: list[Expense] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_times(self):
        if self.startMinutes >= self.endMinutes:
            raise ValueError("每日开始时间须早于结束时间")
        return self

class SaveTrip(CreateTrip):
    baseRevision: int = Field(ge=1, strict=True)
    days: list[DayPlan] = Field(min_length=2, max_length=5)

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    fields = {".".join(str(v) for v in error["loc"]): error["msg"] for error in exc.errors()}
    return JSONResponse(status_code=400, content={"code":"VALIDATION_ERROR",
        "message":"请检查输入字段", "fieldErrors":fields})

@app.exception_handler(HTTPException)
async def business_error(request, exc):
    code = {400:"VALIDATION_ERROR",404:"TRIP_NOT_FOUND",409:"REVISION_CONFLICT"}.get(exc.status_code,"REQUEST_FAILED")
    return JSONResponse(status_code=exc.status_code,content={"code":code,"message":str(exc.detail)})

def result(code, data):
    return {"code": code, "data": data}

@app.get("/api/v1/attractions")
def attractions():
    return result("OK", [{"id": f"spot-{i}", "name": name, "ticketCents": price, "defaultDurationMinutes": 60}
        for i, (name, price) in enumerate([("湖畔公园",0),("城市博物馆",2000),("古街",0),("植物园",3000)],1)])

@app.get("/api/v1/trips")
def trips():
    with connect() as conn:
        return result("OK", [dict(json.loads(data), id=str(id), revision=rev)
            for id, rev, data in conn.execute("SELECT id,revision,data FROM trips ORDER BY id DESC")])

@app.post("/api/v1/trips", status_code=201)
def create(body: CreateTrip):
    data = body.model_dump(mode="json")
    data["name"] = body.name.strip()
    if not data["name"]:
        raise HTTPException(400, "名称不能为空")
    data["days"] = [{"id": f"day-{i}", "dayIndex": i, "startMinutes":540,
        "endMinutes":1260, "items":[], "expenses":[]} for i in range(1,body.dayCount+1)]
    with connect() as conn:
        cur = conn.execute("INSERT INTO trips(revision,data) VALUES(1,?)",(json.dumps(data),))
        id = cur.lastrowid
    return result("TRIP_CREATED", dict(data,id=str(id),revision=1))

@app.get("/api/v1/trips/{id}")
def load(id: int):
    with connect() as conn:
        row = conn.execute("SELECT revision,data FROM trips WHERE id=?",(id,)).fetchone()
    if not row:
        raise HTTPException(404,"旅行不存在")
    return result("TRIP_LOADED",dict(json.loads(row[1]),id=str(id),revision=row[0]))

@app.put("/api/v1/trips/{id}")
def save(id: int, body: SaveTrip):
    if len(body.days) != body.dayCount:
        raise HTTPException(400, "天数不一致")
    day_ids, item_ids, expense_ids = set(), set(), set()
    for index, day in enumerate(body.days, 1):
        if day.dayIndex != index or day.id in day_ids:
            raise HTTPException(400, "日期序号或编号重复")
        day_ids.add(day.id)
        spots = set()
        for order, item in enumerate(day.items):
            if item.id in item_ids or item.attractionId in spots or item.order != order:
                raise HTTPException(400, "重复条目或顺序错误")
            if item.attractionId not in {f"spot-{i}" for i in range(1,5)}:
                raise HTTPException(400, "景点不存在")
            item_ids.add(item.id)
            spots.add(item.attractionId)
        for expense in day.expenses:
            if expense.id in expense_ids:
                raise HTTPException(400, "费用编号重复")
            expense_ids.add(expense.id)
    data = body.model_dump(mode="json", exclude={"baseRevision"})
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT revision FROM trips WHERE id=?", (id,)).fetchone()
        if current is None:
            raise HTTPException(404, "旅行不存在")
        if current[0] != body.baseRevision:
            raise HTTPException(409, "版本冲突，请重新打开旅行")
        revision = current[0] + 1
        conn.execute("UPDATE trips SET data=?,revision=? WHERE id=?", (json.dumps(data),revision,id))
    return result("TRIP_SAVED", dict(data,id=str(id),revision=revision))
