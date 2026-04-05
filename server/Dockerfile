FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY models.py .
COPY client.py .
COPY openenv.yaml .
COPY tasks/ ./tasks/
COPY graders/ ./graders/
COPY server/ ./server/
EXPOSE 7860
ENV PORT=7860
ENV HOST=0.0.0.0
ENV WORKERS=4
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4"]
