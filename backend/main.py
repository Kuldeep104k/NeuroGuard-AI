from fastapi import FastAPI

from backend.api.routes import router


app = FastAPI(title="NeuroGuard AI", description="Safety-first concussion recovery decision support", version="0.1.0")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
