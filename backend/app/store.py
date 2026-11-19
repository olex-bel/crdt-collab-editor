import datetime
import time
from pycrdt.store import BaseYStore,  YDocNotFound
from typing import Callable, Awaitable, AsyncGenerator, Any
from logging import Logger, getLogger
from anyio import Lock
from sqlmodel import select, col, delete
from .database import async_session, AsyncSession
from .models import YUpdate

from pycrdt import Doc

class SQLModelYStore(BaseYStore):
    document_ttl: int | None = None
    squash_threshold: int = 100
    path: str
    lock: Lock

    def __init__(self, path: str, metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None, log: Logger | None = None):
        self.path = path
        self.metadata_callback = metadata_callback
        self.log = log or getLogger(__name__)
        self.lock = Lock()
        self._writes_since_squash = 0

    async def _squash_document_history(self, session: AsyncSession) -> None:
        updates_stmt = select(YUpdate).where(YUpdate.path == self.path).order_by(col(YUpdate.timestamp).asc())
        updates_result = await session.exec(updates_stmt)
        updates = updates_result.all()

        if len(updates) <= 1:
            return

        ydoc: Doc[Any] = Doc()
        for update in updates:
            yupdate = update.yupdate
            ydoc.apply_update(yupdate)

        squashed_update = ydoc.get_update()
        latest_timestamp = updates[-1].timestamp

        update_ids = [u.id for u in updates if u.id is not None]
        delete_stmt = delete(YUpdate).where(col(YUpdate.id).in_(update_ids))
        await session.exec(delete_stmt)
        await session.flush()

        yUpdate = YUpdate(
            path=self.path,
            yupdate=squashed_update,
            timestamp=latest_timestamp
        )

        session.add(yUpdate)

    async def apply_updates(self, ydoc: Doc[Any]) -> None:
            try:
                async for update, _metadata, _timestamp in self.read():
                    ydoc.apply_update(update)
            except YDocNotFound:
                self.log.debug("No stored updates found for path=%s", self.path)
    
    async def write(self, data: bytes) -> None:
        async with self.lock:
            async with async_session() as session:
                last_update_stmt = select(YUpdate).where(YUpdate.path == self.path).order_by(col(YUpdate.timestamp).desc()).limit(1)
                last_update_result = await session.exec(last_update_stmt)
                last_update = last_update_result.first()
                current_time = time.time()
                last_update_time_diff = (current_time - last_update.timestamp) if last_update else 0

                if self.document_ttl is not None and last_update_time_diff > self.document_ttl:
                    await self._squash_document_history(session)

                metadata = await self.get_metadata()
                yUpdate = YUpdate(
                    path=self.path,
                    yupdate=data,
                    timestamp=datetime.datetime.now().timestamp(),
                    metadata_blob=metadata
                )
                session.add(yUpdate)
                await session.commit()

    async def read(self) -> AsyncGenerator[tuple[bytes, bytes, float], None]:
        print(f"Reading updates for path: {self.path}")
        async with self.lock:
            async with async_session() as session:
                documents_stmt = select(YUpdate).where(YUpdate.path == self.path).order_by(col(YUpdate.timestamp).asc())
                documents_result = await session.exec(documents_stmt)
                documents = documents_result.all()

                if not documents:
                    raise YDocNotFound

                for doc in documents:
                    yield doc.yupdate, doc.metadata_blob, doc.timestamp

