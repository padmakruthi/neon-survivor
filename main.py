# ═══════════════════════════════════════════════════════════
# GoldenBatch AI — Backend API
# Team DeepThinkers · IARE · AVEVA Hackathon
# ═══════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import os

import database
import model

# ── Absolute path to this file's folder ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="GoldenBatch AI",
    description="Smart Batch Intelligence for Pharmaceutical Manufacturing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# ───────────────── Startup ─────────────────

@app.on_event("startup")
def startup():
    print("🚀 GoldenBatch AI Backend Starting...")
    database.create_tables()
    print("✅ Database ready")
    database.create_default_users()
    print("✅ Default users ready")
    model.load_or_train_model()
    print("✅ ML Model ready")
    print("═══════════════════════════════════")
    print("✅ Server running at http://localhost:8000")
    print("🌐 Frontend at    http://localhost:8000/app")
    print("📖 API docs at    http://localhost:8000/docs")
    print("═══════════════════════════════════")

# ───────────────── Models ─────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    name: str
    role: str
    message: str


class PredictRequest(BaseModel):
    granulation_time: float
    binder_amount: float
    drying_temp: float
    drying_time: float
    compression_force: float
    machine_speed: float
    lubricant_conc: float
    moisture_content: float


class PredictResponse(BaseModel):
    dissolution_rate: float
    hardness: float
    friability: float
    content_uniformity: float
    energy_estimate: float
    co2_estimate: float
    overall_pass: bool
    individual_results: dict
    recommendations: list
    root_cause: str
    vs_golden: dict


class MessageRequest(BaseModel):
    to: str
    text: str
    priority: str = "normal"
    sender_name: str
    sender_role: str


class MessageResponse(BaseModel):
    success: bool
    message_id: int


# ───── Chatbot Models ─────

class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


# ───────────────── Security ─────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    return database.get_user_from_token(credentials.credentials)


# ───────────────── Root ─────────────────

@app.get("/")
def root():
    return {
        "message": "GoldenBatch AI is running",
        "frontend": "http://localhost:8000/app"
    }


# ───────────────── Frontend ─────────────────

@app.get("/app")
def serve_frontend():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/css/{filename}")
def serve_css(filename: str):
    file_path = os.path.join(BASE_DIR, "css", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/js/{filename}")
def serve_js(filename: str):
    file_path = os.path.join(BASE_DIR, "js", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS file not found")


# ───────────────── Login ─────────────────

@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):

    user = database.verify_login(request.email, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = database.generate_token(user["email"], user["role"])

    database.log_prediction_or_event("login", user["email"], user["role"])

    return LoginResponse(
        success=True,
        token=token,
        name=user["name"],
        role=user["role"],
        message=f"Welcome back, {user['name']}!"
    )


# ───────────────── Prediction ─────────────────

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, user=Depends(get_current_user)):

    inputs = {
        "Granulation_Time": request.granulation_time,
        "Binder_Amount": request.binder_amount,
        "Drying_Temp": request.drying_temp,
        "Drying_Time": request.drying_time,
        "Compression_Force": request.compression_force,
        "Machine_Speed": request.machine_speed,
        "Lubricant_Conc": request.lubricant_conc,
        "Moisture_Content": request.moisture_content,
    }

    result = model.predict(inputs)

    if user:
        database.save_prediction(
            user_email=user["email"],
            inputs=inputs,
            outputs=result
        )

    return PredictResponse(**result)


# ───────────────── Messaging ─────────────────

@app.post("/messages", response_model=MessageResponse)
def send_message(request: MessageRequest, user=Depends(get_current_user)):

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    message_id = database.save_message(
        from_name=request.sender_name,
        from_role=request.sender_role,
        to=request.to,
        text=request.text,
        priority=request.priority,
        time=datetime.now().strftime("%H:%M")
    )

    return MessageResponse(success=True, message_id=message_id)


@app.get("/messages")
def get_messages(role: str = "all"):
    messages = database.get_messages(role)
    return {"messages": messages, "count": len(messages)}


# ───────────────── History ─────────────────

@app.get("/history")
def get_history(user=Depends(get_current_user)):

    if not user:
        return {"predictions": [], "count": 0}

    predictions = database.get_prediction_history(user["email"])

    return {"predictions": predictions, "count": len(predictions)}


# ───────────────── Golden Batch ─────────────────

@app.get("/golden")
def get_golden():
    return model.get_golden_signature()


@app.get("/top-batches")
def get_top_batches():
    return {"batches": model.get_top_batches()}


# ───────────────── AI Training Chatbot ─────────────────

@app.post("/chat", response_model=ChatResponse)
def chatbot(request: ChatRequest):

    q = request.question.lower()

    if "granulation" in q:
        answer = "Granulation time controls particle formation and affects tablet strength."

    elif "binder" in q:
        answer = "Binder amount helps particles stick together and improves tablet hardness."

    elif "drying" in q:
        answer = "Drying temperature and drying time remove moisture from the granules."

    elif "compression" in q:
        answer = "Compression force determines tablet hardness and structural strength."

    elif "machine speed" in q:
        answer = "Machine speed affects production rate and tablet consistency."

    elif "moisture" in q:
        answer = "Moisture content impacts tablet stability and friability."

    elif "lubricant" in q:
        answer = "Lubricant concentration reduces friction during tablet compression."

    elif "predict" in q or "batch" in q:
        answer = "Enter batch parameters in the predictor and the AI model will analyze quality."

    else:
        answer = "I am the GoldenBatch AI training assistant. Ask about parameters like granulation time, binder amount, drying temperature, or batch prediction."

    return ChatResponse(answer=answer)


# ───────────────── Run Server ─────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)