FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# The command is specified in docker-compose.yml
# to differentiate between controller and actor modes.
# This allows the same image to be used for both services.
