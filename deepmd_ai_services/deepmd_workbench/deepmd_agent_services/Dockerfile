# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for building JupyterLab extensions)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install JupyterLab and required Python packages first
RUN pip install --no-cache-dir \
    google-adk \
    fastapi \
    fastmcp \
    python-jose \
    uvicorn \
    dotenv \
    litellm \
    hatch 


# Copy extension source cod
COPY . /app/

# Install the extension (this will trigger the build via hatch)
# RUN pip install -e .

# Set environment variables with default values
ENV ADK_APP_URL=http://localhost:8001
ENV ADK_APP_PORT=8001

# Expose the port
EXPOSE 8001

# Create startup script with all config via command line

# Start command
CMD ["adk",  "web", "--port", "8001", "--session_service_uri=sqlite:////app/deepmd_agent_sessions.db", "--allow_origins=*", "--host", "0.0.0.0",  "./"]
