import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from .data import store

ROOT = Path(__file__).parent

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(store.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title='ElectionCast 2026', lifespan=lifespan)

@app.get('/')
async def index():
    return FileResponse(ROOT / 'index.html')

@app.get('/api/results')
async def results():
    return store.snapshot()

@app.get('/api/health')
async def health():
    return {'ok': True, 'mode': store.status['mode'], 'last_success': store.status['last_success'],
            'errors': store.status['errors']}

@app.get('/api/narration')
async def narration():
    # Narration is data-based, never generated from unsourced headline claims.
    if os.getenv('DEMO_MODE') == '1':
        return {'items': [], 'status': 'demo-disabled'}
    if os.getenv('NARRATION_ENABLED', 'true').lower() != 'true':
        return {'items': [], 'status': 'disabled'}
    return {'items': store.snapshot()['events'], 'status': 'enabled'}
