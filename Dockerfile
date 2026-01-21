# Dockerfile
FROM python:3.9-slim

# Install Tesseract & system deps
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port for Render
EXPOSE 10000

# Run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
