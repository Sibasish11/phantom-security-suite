FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 bankuser
USER bankuser
EXPOSE 8001
CMD ["sh", "-c", "python -m app.seed --target all && uvicorn app.main:app --host 0.0.0.0 --port 8001"]
