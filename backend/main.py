import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

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
    dayCount: int = Field(ge=2, le=5)
    budgetLimitCents: int = Field(ge=0, le=100000000)

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
def save(id: int, body: dict):
    try:
        checked = CreateTrip.model_validate(body)
    except ValidationError:
        raise HTTPException(400, "旅行字段不合法")
    days = body.get("days",[])
    if len(days) != checked.dayCount:
        raise HTTPException(400,"天数不一致")
    seen = set()
    for index, day in enumerate(days,1):
        items = day.get("items",[])
        if day.get("dayIndex") != index or len(items)>20:
            raise HTTPException(400,"日程不合法")
        spots = set()
        if not 0 <= day.get("startMinutes", -1) < day.get("endMinutes", -1) <= 1440:
            raise HTTPException(400, "每日时间不合法")
        for order,item in enumerate(items):
            if item.get("id") in seen or item.get("attractionId") in spots or item.get("order") != order:
                raise HTTPException(400,"重复条目或顺序错误")
            if item.get("attractionId") not in {f"spot-{i}" for i in range(1,5)}:
                raise HTTPException(400,"景点不存在")
            if not isinstance(item.get("durationMinutes"), int) or not 1 <= item["durationMinutes"] <= 720:
                raise HTTPException(400, "停留时长不合法")
            seen.add(item["id"])
            spots.add(item["attractionId"])
    data = dict(body)
    for key in ["id","revision","baseRevision"]:
        data.pop(key,None)
    with connect() as conn:
        cur = conn.execute("UPDATE trips SET data=?,revision=revision+1 WHERE id=? AND revision=?",
            (json.dumps(data),id,body.get("baseRevision")))
        if cur.rowcount != 1:
            raise HTTPException(409,"版本冲突，请重新打开旅行")
    return load(id)
