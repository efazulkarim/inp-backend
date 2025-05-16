import sys
print(f"Python version: {sys.version}")

try:
    import google.generativeai as genai
    print("Successfully imported google.generativeai")
except Exception as e:
    print(f"Error importing google.generativeai: {e}")

try:
    from fastapi import FastAPI
    print(f"Successfully imported FastAPI version: {FastAPI.__version__}")
except Exception as e:
    print(f"Error importing FastAPI: {e}")

try:
    import pydantic
    print(f"Successfully imported Pydantic version: {pydantic.__version__}")
except Exception as e:
    print(f"Error importing Pydantic: {e}") 