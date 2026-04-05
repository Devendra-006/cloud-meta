import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from openenv.core.env_server import create_fastapi_app
from server.environment import CloudCostEnvironment
from models import CloudCostAction, CloudCostObservation

app = create_fastapi_app(CloudCostEnvironment, CloudCostAction, CloudCostObservation)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'dist')
if os.path.exists(ui_path):
    app.mount("/web", StaticFiles(directory=ui_path, html=True), name="ui")

@app.get("/")
async def root():
    return RedirectResponse(url="/web", status_code=302)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
