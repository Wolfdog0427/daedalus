# assistant-core/server/run_server.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("kernel_http_api:app", host="127.0.0.1", port=8000)
