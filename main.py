from fastapi import FastAPI
import threading
from bookbot import start_bot_logic
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "BookBot is running"}

# Background me bot logic start karna
threading.Thread(target=start_bot_logic).start()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
