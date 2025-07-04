"""
Teaching EMR System - Main Application
A lightweight EMR for educational purposes with FHIR and CDS Hooks support
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from api.fhir import fhir_router
from api.cds_hooks import cds_hooks_router
from api.app import app_router
from api.quality import quality_router
from api.cql_api import router as cql_router
from api.clinical.documentation import notes_router
from api.clinical.orders import orders_router
from api.clinical.inbox import inbox_router
from api.clinical.tasks import tasks_router
from api.clinical.catalogs import catalog_router
from api.app.routers import allergies
from api.app import diagnosis_codes, clinical_data, actual_patient_data
from api import auth
from api.imaging import router as imaging_router
from api.dicomweb import router as dicomweb_router
from database.database import engine, Base
# Import all models so they get registered with Base
from models.session import UserSession, PatientProviderAssignment
from models.dicom_models import DICOMStudy, DICOMSeries, DICOMInstance, ImagingResult

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teaching EMR System",
    description="A modern EMR system for teaching clinical workflows, FHIR, and CDS Hooks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.health import router as health_router
app.include_router(health_router, prefix="/api", tags=["Health Check"])
app.include_router(fhir_router.router, prefix="/fhir", tags=["FHIR R4"])
app.include_router(cds_hooks_router.router, prefix="/cds-hooks", tags=["CDS Hooks"])
app.include_router(app_router.router, prefix="/api", tags=["Application API"])
app.include_router(quality_router.router, prefix="/api", tags=["Quality Measures"])
app.include_router(cql_router, tags=["CQL Engine"])

# Include clinical routers
app.include_router(notes_router.router, prefix="/api", tags=["Clinical Notes"])
app.include_router(orders_router.router, prefix="/api", tags=["Clinical Orders"])
app.include_router(inbox_router.router, prefix="/api", tags=["Clinical Inbox"])
app.include_router(tasks_router.router, prefix="/api", tags=["Clinical Tasks"])
app.include_router(catalog_router.router, prefix="/api/catalogs", tags=["Clinical Catalogs"])
app.include_router(allergies.router, prefix="/api", tags=["Allergies"])
app.include_router(diagnosis_codes.router, prefix="/api", tags=["Diagnosis Codes"])
app.include_router(clinical_data.router, prefix="/api", tags=["Clinical Data"])
app.include_router(actual_patient_data.router, prefix="/api", tags=["Actual Patient Data"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(imaging_router, prefix="/api/imaging", tags=["Medical Imaging"])
app.include_router(dicomweb_router, prefix="/api/dicomweb", tags=["DICOMweb"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Teaching EMR System",
        "version": "1.0.0",
        "endpoints": {
            "fhir": "/fhir",
            "cds_hooks": "/cds-hooks",
            "api": "/api",
            "docs": "/docs"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)