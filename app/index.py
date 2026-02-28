"""
Vercel entrypoint. Exports the FastAPI app for serverless deployment.
Vercel looks for app at app/index.py, app/server.py, or app/app.py.
"""
from app.main import app
