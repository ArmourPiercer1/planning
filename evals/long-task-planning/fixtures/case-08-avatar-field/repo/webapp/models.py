"""Profile model + in-memory store."""


class Profile:
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def to_dict(self):
        return {"id": self.user_id, "name": self.name, "email": self.email}


class ProfileStore:
    def __init__(self):
        self._profiles = {}

    def add(self, profile):
        self._profiles[profile.user_id] = profile

    def get(self, user_id):
        return self._profiles.get(user_id)

    def all(self):
        return list(self._profiles.values())
