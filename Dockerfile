FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Cloud platforms typically supply $PORT (Render, Koyeb, Hugging Face)
ENV PORT=7860
EXPOSE 7860 8000

CMD ["sh", "-c", "python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}"]
