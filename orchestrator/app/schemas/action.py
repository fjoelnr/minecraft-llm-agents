from typing import Any, Literal

from pydantic import BaseModel, Field


class ActionChat(BaseModel):
    type: Literal["chat"] = "chat"
    text: str = Field(min_length=1)


class ActionMine(BaseModel):
    type: Literal["mine"] = "mine"
    resource: str = Field(min_length=1)
    qty: int = Field(ge=0)


class Action(BaseModel):
    # offen lassen, damit weitere Typen (z.B. craft) pass-through möglich sind
    type: str

    # Chat
    message: str | None = None
    text: str | None = None

    # Mine / Craft
    resource: str | None = None
    target: str | None = None  # <- Alias für resource (Tests nutzen "target")
    recipe: str | None = None
    qty: int | None = None

    def normalize(self) -> dict[str, Any]:
        # --- chat ---
        if self.type == "chat":
            model = ActionChat(text=(self.text or self.message or ""))
            return {"type": "chat", "text": model.text}

        # --- mine ---
        if self.type == "mine":
            res = self.resource or self.target or ""
            model = ActionMine(resource=res, qty=self.qty if self.qty is not None else 0)
            return {"type": "mine", "resource": model.resource, "qty": model.qty}

        # --- craft (pass-through mit Default qty=1) ---
        if self.type == "craft":
            # minimale Felder laut Tests: recipe + qty default 1
            out: dict[str, Any] = {"type": "craft"}
            if self.recipe is not None:
                out["recipe"] = self.recipe
            out["qty"] = self.qty if self.qty is not None else 1
            return out

        # Fallback: Unbekannte Typen rohdaten zurück
        return self.model_dump(exclude_none=True)
