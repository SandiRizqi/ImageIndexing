# Use osgeo/gdal small as the base image
FROM indigoilya/gdal-docker:latest

RUN apt-get update && apt-get install -y libproj-dev proj-bin awscli

ENV PROJ_LIB=/usr/share/proj

WORKDIR /app
# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
    
    # Copy application files
COPY . .


# Default command
CMD ["python", "main.py"]


