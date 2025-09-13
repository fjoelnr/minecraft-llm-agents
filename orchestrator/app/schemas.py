# orchestrator/app/schemas.py
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field

class ActionChat(BaseModel):
    type: Literal["chat"]
    text: str

class ActionMine(BaseModel):
    type: Literal["mine"]
    target: str
    qty: int = Field(gt=0)

class ActionCraft(BaseModel):
    type: Literal["craft"]
    recipe: str
    qty: int = Field(gt=0, default=1)

# Union per Hand (einfach) – du kannst später pydantic Root-Union nutzen
class Action(BaseModel):
    type: Literal["chat","mine","craft"]
    text: str | None = None
    target: str | None = None
    recipe: str | None = None
    qty: int | None = None

    def normalize(self) -> Dict[str, Any]:
        """Project into specific shape with required fields for logging/execution."""
        if self.type == "chat":
            return {"type":"chat","text": self.text or ""}
        if self.type == "mine":
            return {"type":"mine","target": self.target or "", "qty": self.qty or 1}
        if self.type == "craft":
            return {"type":"craft","recipe": self.recipe or "", "qty": self.qty or 1}
        return {"type": "chat", "text": ""}  # fallback
