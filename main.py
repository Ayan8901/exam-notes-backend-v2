from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ocr.ocr import router as ocr_router

app = FastAPI()

# ✅ include OCR router
app.include_router(ocr_router)

# ✅ CORS for Expo / mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)