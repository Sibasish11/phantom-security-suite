FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY phantomlayer_agent ./phantomlayer_agent

CMD ["python", "-m", "phantomlayer_agent.main"]