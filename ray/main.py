import ray
from ray import serve
from fastapi import FastAPI, Request, HTTPException
import redis
import pywhisper

import tempfile, datetime, hashlib

ray.init(address="auto")
app = FastAPI()

model_path = "/opt/whisper/"
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

@serve.deployment(
  autoscaling_config={
        "min_replicas": 0,
        "initial_replicas": 1,
        "max_replicas": 10,
        "target_num_ongoing_requests_per_replica": 10,
    }
)
@serve.ingress(app)
class WhisperDeployment:
  @app.get("/ping")
  async def ping(self):
    if TranslateService.get_model() is None:
      raise HTTPException(status_code=404, detail="Model not found")

  @app.get("/")
  async def usage(self):
    return {"usage": "POST /stt\n GET /result/{id}"}

  @app.get("/result/{id}")
  async def result(self, id: str):
    text = rd.get(id)
    if text is None:
      raise HTTPException(status_code=404, detail="ID not found")
    return { "text": text }

  @app.post("/stt")
  async def stt(self, request: Request):
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

serve.run(WhisperDeployment.bind())