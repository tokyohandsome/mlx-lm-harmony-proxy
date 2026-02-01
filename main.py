import json
import re
import httpx
import logging
import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

# Initialize Configuration
load_dotenv()
MLX_SERVER_URL = os.getenv("MLX_SERVER_URL", "http://localhost:8585/v1")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Use Uvicorn's default logger for consistency
logger = logging.getLogger("uvicorn.error")

app = FastAPI()

def apply_harmony_tags(text: str) -> str:
    """
    Translates MLX-specific channel tokens to standard <think> tags.
    """
    if not text: return text
    text = text.replace("<|channel|>analysis<|message|>", "<think>")
    text = text.replace("<|end|><|start|>assistant<|channel|>final<|message|>", "</think>\n\n")
    return text

@app.get("/v1/models")
async def list_models():
    """Fetch and return the list of models from the backend MLX server."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{MLX_SERVER_URL}/models", timeout=10.0)
            return JSONResponse(content=resp.json())
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return JSONResponse(content={"object": "list", "data": []})

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    """
    Proxy completions while sanitizing history and formatting reasoning blocks.
    """
    body = await request.json()
    is_stream = body.get("stream", False)
    client_host = request.client.host
    
    logger.info(f"REQ [{client_host}] | Model: {body.get('model')} | Stream: {is_stream}")

    if "messages" in body:
        for msg in body["messages"]:
            if "content" in msg:
                c = msg["content"]
                c = re.sub(r"<think>.*?</think>", "", c, flags=re.DOTALL)
                c = re.sub(r"<\|channel\|>analysis.*?<\|end\|>", "", c, flags=re.DOTALL)
                msg["content"] = c.replace("<|start|>assistant<|channel|>final<|message|>", "").strip()

    async with httpx.AsyncClient() as client:
        try:
            if not is_stream:
                resp = await client.post(f"{MLX_SERVER_URL}/chat/completions", json=body, timeout=None)
                data = resp.json()
                if "choices" in data:
                    msg_content = data["choices"][0].get("message", {}).get("content", "")
                    data["choices"][0]["message"]["content"] = apply_harmony_tags(msg_content)
                return JSONResponse(content=data)
            
            else:
                async def event_generator():
                    buffer = ""
                    TARGET_TAGS = [
                        "<|channel|>analysis<|message|>", 
                        "<|end|><|start|>assistant<|channel|>final<|message|>"
                    ]
                    
                    async with httpx.AsyncClient() as stream_client:
                        async with stream_client.stream("POST", f"{MLX_SERVER_URL}/chat/completions", json=body, timeout=None) as response:
                            async for line in response.aiter_lines():
                                if not line.startswith("data: "): continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    if buffer: yield f"data: {json.dumps({'choices': [{'delta': {'content': buffer}}]})}\n\n"
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    data_json = json.loads(data_str)
                                    delta = data_json["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        buffer += delta["content"]
                                        buffer = apply_harmony_tags(buffer)
                                        is_partial = any(any(tag.startswith(buffer[i:]) for i in range(len(buffer))) for tag in TARGET_TAGS) or buffer.endswith("<")
                                        if not is_partial:
                                            delta["content"], buffer = buffer, ""
                                            yield f"data: {json.dumps(data_json)}\n\n"
                                except:
                                    continue
                return StreamingResponse(event_generator(), media_type="text/event-stream")
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Log startup info using the same logger
    logger.info(f"Starting mlx-lm-harmony-proxy on 0.0.0.0:8585")
    logger.info(f"Forwarding requests to MLX Server: {MLX_SERVER_URL}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8585, 
        log_level=LOG_LEVEL.lower()
    )
