# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set environment variable for unbuffered stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set a working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port that the app will run on (adjust if needed)
EXPOSE 5000

# If using Google credentials, you might need to set:
# ENV GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
# And then mount the credentials file when running the container:
# docker run -v /local/path/to/credentials.json:/path/to/your/credentials.json ...

# Use Gunicorn to serve the Flask app (adjust worker count as needed)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
