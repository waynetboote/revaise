# Use a minimal Python image
FROM python:3.9-slim

# Install Chromium, ChromeDriver, and necessary dependencies
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    fonts-liberation libappindicator3-1 libasound2 libatk1.0-0 \
    libcairo2 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libnspr4 libnss3 libxcomposite1 libxcursor1 libxdamage1 \
    libxfixes3 libxrandr2 libxrender1 libxss1 libxtst6 xdg-utils \
    wget curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium and ChromeDriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (needed for Render)
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]
