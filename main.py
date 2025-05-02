from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.company import router as company_router
# Load environment variables
load_dotenv()

app = FastAPI(
    title="VeritaForge Research",
    description="Backend API for VeritaForge Research",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(company_router, tags=["Companies"])
# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 