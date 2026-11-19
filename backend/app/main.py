from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from pycrdt.websocket import ASGIServer, WebsocketServer, YRoom
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .models import YUpdate
from .database import init_db, engine, get_session
from .store import SQLModelYStore
from .schemas import DocumentItem
from .config import settings

class CustomWebsocketServer(WebsocketServer):
    async def get_room(self, name: str) -> YRoom:
        if name not in self.rooms:
            self.rooms[name] = YRoom(
                ready=True,
                ystore=SQLModelYStore(path=name),
                log=self.log,
            )
        return await super().get_room(name)

    async def start_room(self, room: YRoom) -> None:
        if isinstance(room.ystore, SQLModelYStore):
            await room.ystore.apply_updates(room.ydoc) # type: ignore[arg-type]
        await super().start_room(room)

websocket_server = CustomWebsocketServer(auto_clean_rooms=True)
asgi_server = ASGIServer(websocket_server)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with websocket_server:
        yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ORIGINS,  
    allow_credentials=True, 
    allow_methods=["*"],    
    allow_headers=["*"],    
)

@app.websocket("/ws/documents/{doc_id}")
async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    scope = dict(websocket.scope)
    scope["path"] = f"/{doc_id.strip('/')}"
    await asgi_server(scope, websocket.receive, websocket.send) # type: ignore[arg-type]

@app.get("/documents/", response_model=list[DocumentItem])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[DocumentItem]:
    stmt = select(YUpdate.path).distinct()
    paths = (await session.exec(stmt)).all()

    return [
        DocumentItem(path=path.lstrip("/")) for path in paths if path
    ]