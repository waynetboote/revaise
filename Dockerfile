# Use a lightweight Python image
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium and ChromeDriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set the working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Render
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]
