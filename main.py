import time
import requests
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

API_KEY = 'tlk_0DYYT8W3FTMHMH22DVSX42ADNB40'
BASE_URL = 'https://api.twelvelabs.io/v1.3/embed/tasks'

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Optional: Allow frontend JS to work with API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def create_video_embedding_task(file: UploadFile, model_name="Marengo-retrieval-2.7", video_clip_length=9):
    headers = {'x-api-key': API_KEY}
    files = {'video_file': (file.filename, file.file, file.content_type)}
    data = {'model_name': model_name, 'video_clip_length': str(video_clip_length)}

    response = requests.post(BASE_URL, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.json().get('_id')
    else:
        print(f"Error creating task: {response.status_code}, {response.text}")
        return None

def monitor_task_status(task_id):
    task_status_url = f"{BASE_URL}/{task_id}/status"
    headers = {'x-api-key': API_KEY}

    start_time = time.time()
    while True:
        response = requests.get(task_status_url, headers=headers)
        if response.status_code == 200:
            status = response.json().get('status')
            if status == 'ready':
                return True
            elif status == 'failed':
                return False
            elif time.time() - start_time > 600:
                return False
            time.sleep(10)
        else:
            return False

def retrieve_video_embeddings(task_id):
    url = f"{BASE_URL}/{task_id}"
    headers = {'x-api-key': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get('video_embedding')
    else:
        return None

@app.post("/upload-video")
async def upload_video(video_file: UploadFile = File(...)):
    task_id = create_video_embedding_task(video_file)
    if task_id:
        return JSONResponse(content={"task_id": task_id})
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to create video embedding task"})

@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
    if monitor_task_status(task_id):
        return JSONResponse(content={"status": "ready"})
    else:
        return JSONResponse(status_code=500, content={"status": "failed"})

@app.get("/retrieve-embeddings/{task_id}")
async def retrieve_embeddings(task_id: str):
    embeddings = retrieve_video_embeddings(task_id)
    if embeddings:
        return JSONResponse(content={"embeddings": embeddings})
    else:
        return JSONResponse(status_code=404, content={"error": "No embeddings found"})
