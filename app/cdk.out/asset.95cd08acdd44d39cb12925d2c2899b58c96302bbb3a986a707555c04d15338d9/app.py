from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Adaptador para AWS Lambda
handler = Mangum(app)