FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Set Python path so imports work
ENV PYTHONPATH=/app

# Run the API
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
