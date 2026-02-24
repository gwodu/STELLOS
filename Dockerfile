# -------------------------------------------------
# 1️⃣ Base image – Python 3.11 is extremely stable for AI/PyTorch
# (3.12 is okay, but 3.11 guarantees full compatibility with LAION-CLAP)
# -------------------------------------------------
FROM python:3.11-slim

# -------------------------------------------------
# 2️⃣ System packages needed for ffmpeg & building wheels
# -------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# 3️⃣ Create non-root user (MANDATORY for Hugging Face Spaces)
# Hugging Face will crash or reject the container if it runs as root.
# -------------------------------------------------
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# -------------------------------------------------
# 4️⃣ Install Python dependencies 
# (Node.js is actually NOT required for your Python backend!)
# -------------------------------------------------
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------
# 5️⃣ Copy the backend source code
# -------------------------------------------------
COPY --chown=user:user . .

# -------------------------------------------------
# 6️⃣ Expose the FastAPI port (Hugging Face uses 7860 by default)
# -------------------------------------------------
EXPOSE 7860

# -------------------------------------------------
# 7️⃣ Start the app
# Railway provides PORT at runtime; default to 7860 locally.
# -------------------------------------------------
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
