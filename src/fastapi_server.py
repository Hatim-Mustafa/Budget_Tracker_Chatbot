import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth_router, chat_router, conversation_router

logfire.configure()
logfire.instrument_pydantic_ai()


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(conversation_router)

    return app


app = create_app()
