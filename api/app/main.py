from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="EducaChat API",
    version="0.1.0",
    description="Tutoria socrática para alunos a partir do 6º ano.",
)

# Equivalente ao CorsRegistry do Spring: o browser bloqueia front (5173) falando
# com back (8000) se a API não listar a origem explicitamente.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
