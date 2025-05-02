# app/main.py
from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth_routes, user_routes, answer_routes, ideaboard_routes, trash_routes, archive_routes, report_routes

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is running!"}

# Create the database tables
Base.metadata.create_all(bind=engine)

# Include the authentication and user routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/user", tags=["user"])
app.include_router(answer_routes.router, prefix="/api/answer", tags=["answer"])
app.include_router(ideaboard_routes.router, prefix="/api/ideaboard", tags=["ideaboard"])
app.include_router(trash_routes.router, prefix="/api/trash", tags=["trash"])
app.include_router(archive_routes.router, prefix="/archive", tags=["Archive"])
app.include_router(report_routes.router, prefix="/api/report", tags=["report"])
