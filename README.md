# mlx-lm-harmony-proxy  
  
A lightweight FastAPI-based proxy to enable **OpenAI Harmony** style reasoning chats using `mlx-lm` on Apple Silicon.  
  
## Overview  
  
This proxy allows reasoning models like `gpt-oss` (via `mlx_lm.server`) to work seamlessly with standard LLM clients (Dify, LibreChat, etc.) by translating internal reasoning channels into structured `<think>` tags and ensuring stable multi-turn history.  
  
## Key Features  
  
- **Harmony Translation**: Converts `<|channel|>analysis` tokens into standard Markdown `<think>` blocks.  
- **Context Sanitization**: Automatically strips previous reasoning steps from chat history to prevent context pollution and instability.  
- **Smart Buffering**: Handles streaming responses with precision, ensuring UI elements don't "flicker" with partial tags.  
  
## Setup  
  
### Using Docker  
  
1. Clone this repository.  
2. Copy `.env.example` to `.env` and configure your `MLX_SERVER_URL`.  
3. Launch the container:  
   `docker compose up -d --build`  
  
### Manual Execution  
  
1. Install requirements:  
   `pip install fastapi uvicorn httpx python-dotenv`  
2. Run the proxy:  
   `python main.py`  
  
## Client Configuration  
  
- **API Base URL**: `http://<your-proxy-ip>:8585/v1`  
- **Model Name**: Use the same identifier as your `mlx_lm.server`.  
- **Stream**: Enabled (Recommended).  
