FROM python:3.12-slim

LABEL org.opencontainers.image.name="mem0/openmemory-mcp"

WORKDIR /usr/src/openmemory

# Copy shared module first (build context is now project root)
COPY ./shared /usr/src/shared

# Install dependencies
COPY ./openmemory/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./openmemory/api .

# Create symlink to shared module for proper import resolution
RUN ln -sf /usr/src/shared shared

# Set Python path to include shared module
ENV PYTHONPATH=/usr/src/shared:/usr/src/openmemory

EXPOSE 8765

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "4"]
