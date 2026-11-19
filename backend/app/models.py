from sqlmodel import SQLModel, Field

class YUpdate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    path: str = Field(index=True)
    yupdate: bytes
    metadata_blob: bytes = Field(default=b"")
    timestamp: float
