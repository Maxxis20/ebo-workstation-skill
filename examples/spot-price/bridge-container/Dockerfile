FROM python:3.12.8-slim
RUN pip install --no-cache-dir tzdata==2025.2
WORKDIR /app
COPY spotd.py /app/spotd.py
CMD ["python", "-u", "/app/spotd.py", "/cfg/config.json"]
