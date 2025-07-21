FROM python:3.12-slim

LABEL org.opencontainers.image.name="mem0/openmemory-mcp"

WORKDIR /usr/src/openmemory

# Copy shared module first (build context is now project root)
COPY ./shared /usr/src/shared

# Copy local mem0 library
COPY ./mem0 /usr/src/mem0

# Copy root requirements.txt to make relative path work
COPY ./requirements.txt /usr/src/requirements.txt

# Install dependencies
COPY ./openmemory/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install local mem0 library (this will override the PyPI version)
RUN pip install -e /usr/src/mem0

# Copy application
COPY ./openmemory/api .

# Create symlink to shared module for proper import resolution
RUN ln -sf /usr/src/shared shared

# Set Python path to include shared module and mem0
ENV PYTHONPATH=/usr/src:/usr/src/openmemory:/usr/src/mem0

EXPOSE 8765

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "4"]
