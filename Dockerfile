# Use an official slim Python runtime as a parent image
FROM python:3.12-slim

# Environment variables
ENV USR_NAME=appuser 
ENV USR_GRPN=appgroup 
ENV USR_GRPID=1024 
ENV SCRAPER_USER_HOME=/usr/local/${USR_NAME}

# Install basics and configure locale
RUN apt-get update && pip install uv
RUN apt-get update && apt install -y firefox-esr

# Install Python dependencies
COPY ./pyproject.toml /pyproject.toml
COPY ./uv.lock /uv.lock
RUN uv export --no-hashes --format requirements-txt > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
RUN playwright install && playwright install-deps

# Copy required files and folders
COPY /src ${SCRAPER_USER_HOME}
COPY entrypoint.sh ${SCRAPER_USER_HOME}/entrypoint.sh

# Create a non-root user in the 1024 group
RUN addgroup --gid ${USR_GRPID} ${USR_GRPN}
RUN useradd -ms /bin/bash -d ${SCRAPER_USER_HOME} -g ${USR_GRPN} ${USR_NAME} 

# Set the actual working directory as src
WORKDIR ${SCRAPER_USER_HOME}

# Define the commands to initialize the application
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]

# Finally execute the python script
CMD ["python", "main.py"]