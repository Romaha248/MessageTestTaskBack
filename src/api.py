from fastapi import FastAPI
from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.chats.router import router as chats_router
from src.chats.websocket import router as websocket_router


def register_routes(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(chats_router)
    app.include_router(websocket_router)
