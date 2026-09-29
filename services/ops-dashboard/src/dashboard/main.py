import asyncio
import json
import os
import threading

import boto3
from botocore.config import Config
from confluent_kafka import Consumer
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from .state import State

state = State()
TOPICS = {
    os.environ.get("TOPIC_SAFETY", "bus.safety.events"): "safety",
    os.environ.get("TOPIC_PASSENGER", "bus.passenger.counts"): "passenger",
    os.environ.get("TOPIC_HEALTH", "bus.edge.health"): "health",
}
app = FastAPI(title="ops-dashboard (read-only)")


def kafka_conf() -> dict:
    conf = {
        "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092"),
        "group.id": os.environ.get("KAFKA_GROUP", "bus-ops-dashboard"),
        "auto.offset.reset": "earliest",
    }
    if os.environ.get("KAFKA_USERNAME"):
        conf.update({
            "security.protocol": "SASL_SSL", "sasl.mechanisms": "SCRAM-SHA-512",
            "sasl.username": os.environ["KAFKA_USERNAME"],
            "sasl.password": os.environ["KAFKA_PASSWORD"],
        })
        if os.environ.get("KAFKA_CA_PATH"):
            conf["ssl.ca.location"] = os.environ["KAFKA_CA_PATH"]
    return conf


def consume():
    c = Consumer(kafka_conf())
    c.subscribe(list(TOPICS))
    while True:
        msg = c.poll(1.0)
        if msg is None or msg.error():
            continue
        state.add(TOPICS[msg.topic()], json.loads(msg.value()))


def s3():
    # S3_PUBLIC_ENDPOINT is the S4 route that the operator's browser can reach.
    return boto3.client(
        "s3", endpoint_url=os.environ.get("S3_PUBLIC_ENDPOINT", os.environ.get("S3_ENDPOINT")),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "s4admin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "s4secret"),
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))


@app.on_event("startup")
def start():
    if os.environ.get("DISABLE_CONSUMER") != "1":
        threading.Thread(target=consume, daemon=True).start()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/state")
def api_state():
    return state.snapshot()


@app.get("/evidence/{event_id}")
def evidence(event_id: str):
    for _, kind, p in state.snapshot()["items"]:
        if kind == "safety" and p["event_id"] == event_id and p.get("evidence"):
            e = p["evidence"]
            url = s3().generate_presigned_url(
                "get_object", Params={"Bucket": e["bucket"], "Key": e["key"]}, ExpiresIn=300)
            return RedirectResponse(url)
    raise HTTPException(404, "no evidence for this event")


@app.get("/stream")
async def stream():
    async def gen():
        seq = 0
        while True:
            for s, kind, payload in state.since(seq):
                seq = s
                yield f"data: {json.dumps({'kind': kind, 'payload': payload})}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")


PAGE = """<!doctype html><meta charset=utf-8><title>Bus operations (read-only)</title>
<style>body{font-family:system-ui;margin:2rem;background:#111;color:#eee}
.high{color:#ff6b6b}.suspicious{color:#ffd166}li{margin:.3rem 0}a{color:#7cc7ff}</style>
<h1>Bus operations</h1><h3>Safety events</h3><ul id=ev></ul>
<h3>Passengers and health</h3><pre id=bus></pre>
<script>
const buses={};
const es=new EventSource('/stream');
es.onmessage=m=>{const {kind,payload:p}=JSON.parse(m.data);
 if(kind==='safety'){const li=document.createElement('li');li.className=p.severity;
  li.innerHTML=`${p.detected_at} bus ${p.bus_id} <b>${p.severity}</b> score ${p.score.toFixed(2)} `+
  (p.evidence?`<a href="/evidence/${p.event_id}" target=_blank>evidence</a>`:'');
  document.getElementById('ev').prepend(li);}
 else{const b=buses[p.bus_id]=buses[p.bus_id]||{};
  if(kind==='passenger'){b.occupancy=p.occupancy;b.boarded=p.boarded;b.alighted=p.alighted;}
  if(kind==='health'){b.health=p.components;b.outbox=p.outbox;}
  document.getElementById('bus').textContent=JSON.stringify(buses,null,2);}};
</script>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
