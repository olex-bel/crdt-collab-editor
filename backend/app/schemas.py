from sqlmodel import SQLModel

class DocumentItem(SQLModel):
    path: str