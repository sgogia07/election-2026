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

@app.get('/api/northern-virginia')
async def northern_virginia():
    return {
        'status': 'Candidate lists are from Virginia Department of Elections; live counts are sourced separately.',
        'source': 'https://www.elections.virginia.gov/casting-a-ballot/candidate-list/',
        'races': [
            {'district':'VA-07','name':'Virginia 7th Congressional District','candidates':[{'name':'Eugene Vindman','party':'D'},{'name':'Doug Ollivant','party':'R'},{'name':'Taner Lopez','party':'L'},{'name':'Alaha Ahrar','party':'I'},{'name':'Joshua Ertle','party':'I'},{'name':'Randall Terry','party':'I'}]},
            {'district':'VA-08','name':'Virginia 8th Congressional District','candidates':[{'name':'Don Beyer','party':'D'},{'name':'Tony Sabio','party':'R'},{'name':'Shelly Arnoldi','party':'L'},{'name':'Tim Sharman','party':'I'}]},
            {'district':'VA-10','name':'Virginia 10th Congressional District','candidates':[{'name':'Suhas Subramanyam','party':'D'},{'name':'Dave Beckwith','party':'R'},{'name':'Ahsen Malik','party':'I'}]},
            {'district':'VA-11','name':'Virginia 11th Congressional District','candidates':[{'name':'James Walkinshaw','party':'D'},{'name':'Arthur Purves','party':'R'},{'name':'Dianne Blais','party':'G'}]},
            {'district':'VA-SEN','name':'U.S. Senate — Virginia','candidates':[{'name':'Mark Warner','party':'D'},{'name':'Bert Mizusawa','party':'R'}]},
        ],
        'official_results':'https://www.elections.virginia.gov/results/',
        'localities':'Separate locality totals must be district-filtered, not shown as congressional district results.'
    }
