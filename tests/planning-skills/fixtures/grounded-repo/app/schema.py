"""Output schemas for profile endpoints."""


class ProfileOut:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name}
