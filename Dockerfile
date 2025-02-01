# Use the official Python image as a base
FROM python:3.9-slim

# Install Chromium, ChromeDriver, and dependencies
RUN apt-get update && apt-get install -y \
    wget unzip \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set the working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (needed for Render)
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]
