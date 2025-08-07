FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The command is now specified in docker-compose.yml
# to differentiate between controller and actor modes.
# CMD ["python", "main.py"]
