import hashlib, tempfile, datetime

import pywhisper
import redis

from fastapi import FastAPI, Request, HTTPException

model_path = "/opt/whisper/"
app = FastAPI()
rd = redis.StrictRedis(host='localhost', port=6379, db=0)

class TranslateService(object):
  model = None

  @classmethod
  def get_model(cls):
    if cls.model is None:
      cls.model = pywhisper.load_model("base", download_root=model_path)
    return cls.model

  @classmethod
  def transcribe(cls, voice_file):
    model = cls.get_model()
    stt_result = model.transcribe(voice_file)
    return stt_result["text"]

@app.get("/ping")
def ping():
  if TranslateService.get_model() is None:
    raise HTTPException(status_code=404, detail="Model not found")

@app.get("/")
async def usage():
  return {"usage": "POST /stt"}

@app.get("/result/{id}")
async def result(id: str):
  text = rd.get(id)
  if text is None:
    raise HTTPException(status_code=404, detail="ID not found")
  return { "text": text }

@app.post("/stt")
async def stt(request: Request):
  with tempfile.NamedTemporaryFile() as file:
    data: bytes = await request.body()
    new_id = hashlib.md5(data).hexdigest()
    print("size:" + str(len(data)) + " bytes, id:" + new_id)

    cache_text = rd.get(new_id)
    if cache_text is not None:
      return { "id": new_id, "text": cache_text }

    file.write(data)
    text = TranslateService.transcribe(file.name)
    rd.set(new_id, text, datetime.timedelta(hours=24))
    return { "id": new_id, "text": text }