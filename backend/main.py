"""
Amazon PPC Analyzer - Backend API
FastAPI application for analyzing Amazon PPC data and generating bulk upload files.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import upload, analysis, export

app = FastAPI(
    title="Amazon PPC Analyzer API",
    description="API for analyzing Amazon PPC performance and generating bulk upload files",
    version="1.0.0"
)

import os

# CORS middleware for Next.js frontend
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Amazon PPC Analyzer API"}


@app.get("/api/health")
async def health_check():
    """API health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
