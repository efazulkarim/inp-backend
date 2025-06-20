# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth_routes, user_routes, answer_routes, ideaboard_routes, trash_routes, archive_routes, report_routes, customerboard_routes, stripe_routes
from starlette.middleware.sessions import SessionMiddleware
import secrets

# Robust .env loading (similar to Stripe Routes)
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # project root
    os.path.join(os.path.dirname(__file__), '.env'),  # app directory
    '.env'  # current working directory
]
env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[main.py] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[main.py] ⚠️ WARNING: No .env file found in any standard location!")

app = FastAPI()

# Add SessionMiddleware for OAuth (required by Authlib)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# CORS middleware configuration
origins = [
    "http://localhost",
    "https://inp-dashboard.netlify.app",
    "http://localhost:3000",  # React development server
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "https://localhost",
    "https://localhost:3000",
    # Production URLs - REPLACE THESE WITH YOUR ACTUAL DOMAINS
    "https://www.yourdomain.com",
    "https://app.yourdomain.com",
    # Add any other origins your frontend might be served from
]

# For development, you can also use a wildcard
if os.getenv("ENVIRONMENT") == "production":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Allow frontend to read custom headers
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
