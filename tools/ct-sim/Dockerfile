# ct-sim/Dockerfile
FROM python:3.11-slim

# Install essential dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# DICOM DIMSE port (standard CT-SIM port)
EXPOSE 105

# Health check using C-ECHO
HEALTHCHECK --interval=30s --timeout=10s \
  CMD python -c "from pynetdicom import AE; \
  ae = AE(); \
  ae.add_requested_context('1.2.840.10008.1.1'); \
  assoc = ae.associate('localhost', 105, ae_title=b'CT_SIM'); \
  if not assoc.is_established: exit(1); \
  assoc.release()"

# Run the simulator (using simulate_server.py instead of main.py)
CMD ["python", "-u", "simulate_server.py"]