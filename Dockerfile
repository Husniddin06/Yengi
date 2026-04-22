FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Muhim: PYTHONPATH /app bo'lishi kerak, shunda 'from bot.database import db' kabi importlar ishlaydi
ENV PYTHONPATH=/app
CMD ["python", "bot/main.py"]
