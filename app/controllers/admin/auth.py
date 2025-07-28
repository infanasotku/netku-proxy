from fastapi import Request
from sqladmin.authentication import AuthenticationBackend


class AdminAuthenticationBackend(AuthenticationBackend):
    """Authentication backend for admin panel."""

    def __init__(self, secret: str, *, username: str, password: str):
        super().__init__(secret)
        self.username = username
        self.password = password

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        if not username or not password:
            return False

        if self.username != username:
            return False

        if password != self.password:
            return False

        request.session["username"] = username

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        if not request.session:
            return False

        return True
