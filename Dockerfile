# Use a minimal Python image
FROM python:3.9-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# ✅ First, copy only requirements.txt (enables Docker caching)
WORKDIR /app
COPY requirements.txt /app/

# ✅ Install dependencies BEFORE copying other files
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    fonts-liberation libappindicator3-1 libasound2 libatk1.0-0 \
    libcairo2 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libnspr4 libnss3 libxcomposite1 libxcursor1 libxdamage1 \
    libxfixes3 libxrandr2 libxrender1 libxss1 libxtst6 xdg-utils \
    wget curl unzip \
    && rm -rf /var/lib/apt/lists/*

# ✅ Install Python dependencies separately for caching
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Now copy the rest of the application files
COPY . /app/

# ✅ Set environment variables for Chromium & ChromeDriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# ✅ Expose port for Render
EXPOSE 5000

# ✅ Start the application
CMD ["python", "app.py"]
