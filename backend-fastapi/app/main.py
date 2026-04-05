from fastapi import FastAPI

app = FastAPI(title="RelationshipAI - FastAPI Service")

@app.get("/")
async def root():
    return {"message": "RelationshipAI FastAPI Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
