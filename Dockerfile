FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx python-dotenv

COPY main.py .

EXPOSE 8585

# Execute python script directly
CMD ["python", "main.py"]
