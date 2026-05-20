FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.110.0 uvicorn[standard]==0.27.1 python-multipart==0.0.9
COPY main.py .
EXPOSE 9100
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9100"]
