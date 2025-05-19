# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth_routes, user_routes, answer_routes, ideaboard_routes, trash_routes, archive_routes, report_routes, customerboard_routes, stripe_routes

# Load .env from the app folder
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

# CORS middleware configuration
origins = [
    "http://localhost",
    "http://localhost:3000",  # Assuming your frontend runs on port 3000
    # Add any other origins your frontend might be served from
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API is running!"}

# Comment out automatic table creation to avoid conflicts with Alembic migrations
# Use Alembic migrations instead for database schema management
# Base.metadata.create_all(bind=engine)

# Include the authentication and user routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/user", tags=["user"])
app.include_router(answer_routes.router, prefix="/api/answer", tags=["answer"])
app.include_router(ideaboard_routes.router, prefix="/api/ideaboard", tags=["ideaboard"])
app.include_router(trash_routes.router, prefix="/api/trash", tags=["trash"])
app.include_router(archive_routes.router, prefix="/archive", tags=["Archive"])
app.include_router(report_routes.router, prefix="/api/report", tags=["report"])
app.include_router(customerboard_routes.router, prefix="/api/customerboard", tags=["customerboard"])
app.include_router(stripe_routes.router, prefix="/api/stripe", tags=["stripe"])
