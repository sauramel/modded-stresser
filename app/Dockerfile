FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV MODE=actor
ENV CONTROLLER_HOST=http://controller:8000
ENV TARGET_HOST=127.0.0.1
ENV TARGET_PORT=25565
ENV THREADS=200
ENV DURATION=30
ENV ACTOR_ID=actor-default

CMD ["python", "main.py"]
