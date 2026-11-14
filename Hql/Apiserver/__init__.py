from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import fastapi
from typing import TYPE_CHECKING, Optional, Union
import threading
from Hql.Helpers import can_thread
from Hql.Exceptions import HqlExceptions as hqle
import json
from pydantic import BaseModel
from pathlib import Path
import logging
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from Hql.Hac.Engine import HacEngine

class HqlRequest(BaseModel):
    hql: str
    run: bool = True
    save: bool = False
    plan: bool = False
    # The window HaC and Sigma runs search, a lookback like 1h or 7d, or an
    # absolute start and end. Neither keeps the HaC schedule's interval.
    lookback: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    retro: bool = False

def local_naive(value:datetime) -> datetime:
    '''Hql's naive datetimes are local time, so convert ones that carry a zone.'''
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)

def resolve_window(req:HqlRequest) -> tuple[Optional[timedelta], Optional[datetime]]:
    '''
    The lookback and query time a run uses, from a lookback or a start and end.
    None for either keeps the detection's default, its schedule's interval up to now.
    '''
    from Hql.Functions.time import parse_timespan
    from Hql.Exceptions import HqlExceptions as hqle

    if req.start is not None or req.end is not None:
        if req.lookback:
            raise ValueError('Give either a lookback or a start and end, not both')
        if req.start is None or req.end is None:
            raise ValueError('A time range needs both a start and an end')
        start, end = local_naive(req.start), local_naive(req.end)
        if start >= end:
            raise ValueError(f'Start {start.isoformat()} must be before end {end.isoformat()}')
        return end - start, end

    if req.lookback:
        try:
            lookback = parse_timespan(req.lookback)
        except hqle.ArgumentException:
            raise ValueError(f'Invalid lookback {req.lookback!r}, expected e.g. 30m, 1h or 7d')
        if lookback <= timedelta(0):
            raise ValueError(f'Lookback must be positive, got {req.lookback!r}')
        return lookback, None

    return None, None

class Apiserver():
    def __init__(self, hacengine:HacEngine, host='0.0.0.0', port=8080):
        if not can_thread():
            raise hqle.CompilerException('Cannot start the api server as free threading is not supported, use the container?')

        self.hacengine = hacengine
        self.app = FastAPI()
        self.host = host
        self.port = port
        self.thread = None

        # Add CORS middleware for development
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Serve static frontend files
        # Try container path first, then development path
        static_dir = Path("/opt/Hql/Hql-Interface/dist")
        if not static_dir.exists():
            static_dir = Path(__file__).parent.parent.parent / "Hql-Interface" / "dist"

        if static_dir.exists() and (static_dir / "assets").exists():
            self.app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

        @self.app.get("/")
        def read_root():
            # Serve index.html if it exists, otherwise return API info
            index_file = static_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"I'm serving a": "youthful porpoise 🐬"}

        # API endpoints
        @self.app.get('/api/detections/{detection_id}/history')
        def get_detection_history(detection_id:str):
            if detection_id not in self.hacengine.detections:
                raise HTTPException(status_code=404, detail=f'Detection {detection_id} not found')
            return self.hacengine.detections[detection_id].run_history

        @self.app.get('/api/detections')
        def get_detections():
            detections = []
            for i in self.hacengine.detections:
                det = self.hacengine.detections[i]
                if not det.hac:
                    continue
                detections.append(det.hac.asm)
            return detections
        
        @self.app.get('/api/detections/{detection_id}')
        def get_detection(detection_id:str):
            detection = self.hacengine.detections[detection_id]
            return detection.to_dict()

        @self.app.post('/api/detections')
        async def save_detection(request: fastapi.Request):
            query_body = await request.body()
            query_text = query_body.decode('utf-8')

            if not query_text.strip():
                raise HTTPException(status_code=400, detail='Query body cannot be empty')

            try:
                detection = self.hacengine.write_detection(query_text)

                # Reload detections
                self.hacengine.files = self.hacengine.scan_files()
                self.hacengine.detections = self.hacengine.load_files()

                return {'id': detection.id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f'Failed to save detection: {str(e)}')

        @self.app.post('/api/detections/retro')
        def retro_hunt(hql:HqlRequest):
            from Hql.Hac.Engine import Detection

            det = Detection(hql.hql, 'api', self.hacengine.config, no_hac=True)
            if not det.hac or not det.schedule:
                return {'id': ''}

            # Default to the last hour, worked out per request rather than at import
            end:datetime = local_naive(hql.end) if hql.end else datetime.now()
            start:datetime = local_naive(hql.start) if hql.start else end - timedelta(hours=1)
            delta = det.schedule.delta()

            ids = []
            while start < end:
                rid = self.hacengine.run_detection(det, query_now=start + delta)
                ids.append(rid)
                start += delta
                det = Detection(hql.hql, 'api', self.hacengine.config, no_hac=True)

            return {'ids': ids}

        @self.app.get('/api/schema')
        def get_schema():
            # Return available fields from data sources
            # This is a simplified version - could be enhanced to introspect actual data sources
            schema = []

            # Get schema from config if available
            if hasattr(self.hacengine.config, 'schema') and self.hacengine.config.schema:
                for field_name, field_type in self.hacengine.config.schema.items():
                    schema.append({
                        'name': field_name,
                        'type': str(field_type) if hasattr(field_type, '__name__') else str(type(field_type).__name__)
                    })

            return schema

        @self.app.get('/api/hql/runs/{tid}')
        def get_run_by_id(tid:str):
            run = self.hacengine.get_by_id(tid)
            if run == None:
                raise HTTPException(status_code=404, detail=f'Run {tid} not found')
            return run.to_dict()

        @self.app.get('/api/hql/runs')
        def get_runs():
            return self.hacengine.get_runs()

        @self.app.post('/api/hql/runs')
        def submit_hql_query(hql:HqlRequest):
            from Hql.Hac.Engine import Detection
            if not hql.run:
                return {'id': ''}

            try:
                lookback, query_now = resolve_window(hql)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            det = Detection(hql.hql, 'api', self.hacengine.config, no_hac=True, lookback=lookback)
            rid = self.hacengine.run_detection(det, query_now=query_now)
            return {'id': rid}

        @self.app.post('/api/hql/deparse')
        def reparse_hql(hql:HqlRequest):
            from Hql.Hac.Engine import Detection

            det = Detection(hql.hql, 'api', self.hacengine.config)
            deparsed = det.deparse()

            return {
                'hql': deparsed
            }

        @self.app.post('/api/sigma/convert')
        def convert_sigma(hql:HqlRequest):
            return reparse_hql(hql)

        @self.app.post('/api/hql/init_hac')
        def add_hac(hql:HqlRequest):
            from Hql.Hac.Engine import Detection
            from Hql.Hac import Hac

            det = Detection(hql.hql, 'api', self.hacengine.config)
            if not det.hac:
                det.hac = Hac({}, 'api')
                comment = det.hac.render(target='decompile')
                return {'hql': comment + '\n' + hql.hql}
            else:
                return {'hql': hql.hql}


    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        logging.info(f'Starting api server on http://{self.host}:{self.port}')
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    def join(self):
        if self.thread:
            self.thread.join()
