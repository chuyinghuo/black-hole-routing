# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project into container
COPY . .

# Expose port 8081 to host
EXPOSE 8081

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8081
ENV FLASK_ENV=production

# Run with Flask (can switch to Gunicorn below if needed)
CMD ["flask", "run", "--port=8081"]