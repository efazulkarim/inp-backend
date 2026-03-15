# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth_routes, user_routes, answer_routes, ideaboard_routes, trash_routes, archive_routes, report_routes, customerboard_routes, stripe_routes, polar_routes
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
        print(f"[main.py] Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[main.py] ⚠️ WARNING: No .env file found in any standard location!")

app = FastAPI(
    title="InsightPilot API",
    description="API for InsightPilot idea management platform",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Add SessionMiddleware for OAuth (required by Authlib)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# CORS middleware configuration
# Vercel: Add VERCEL_URL (e.g. https://your-project.vercel.app) for frontend on Vercel
def _get_cors_origins() -> list[str]:
    base = [
        "http://localhost",
        "https://app.insightpilot.co",
        "https://inp-dashboard.netlify.app",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "https://localhost",
        "https://localhost:3000",
    ]
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        base.append(frontend_url.rstrip("/"))
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        base.extend([f"https://{vercel_url}", f"https://www.{vercel_url}"])
    return base

origins = _get_cors_origins()

# For development, you can also use a wildcard
# Make sure to list your specific frontend origins for production.
# Using ["*"] in production is a security risk.
# if os.getenv("ENVIRONMENT") == "production":
# origins = ["*"] # This is dangerous for production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Ensure this list is correctly configured for your environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Allow frontend to read custom headers
)

# Security Headers Middleware (enabled only in production)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment != "production":
        # Do not set strict headers in non-production to avoid blocking docs/local dev
        return response

    path = request.url.path

    # Relax headers for docs endpoints in production
    if path.startswith(("/docs", "/redoc", "/openapi.json", "/favicon.ico")):
        if "Content-Security-Policy" in response.headers:
            del response.headers["Content-Security-Policy"]
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        response.headers["X-Frame-Options"] = "DENY"

    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/")
def read_root():
    return {
        "message": "InsightPilot API is running!",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is operational"}

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
app.include_router(polar_routes.router, prefix="/api/polar", tags=["polar"])


@auth_routes.router.get("/debug-oauth")
async def debug_oauth():
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "frontend_url": os.getenv('FRONTEND_URL'),
        "google_redirect_uri": os.getenv('GOOGLE_REDIRECT_URI'),
        "environment": os.getenv('ENVIRONMENT')
    }