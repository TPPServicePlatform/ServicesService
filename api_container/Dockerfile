FROM python:3.10.12 

# Set the working directory
WORKDIR /code/

# Copy the `api_container` contents into `/code/`
COPY ./api_container /code/

# Copy the `lib` directory into `/code/lib/`
COPY ./lib /code/lib/

# Copy the `requirements.txt` directly
COPY ./api_container/requirements.txt /code/requirements.txt

COPY ./api_container/.env /code/.env

RUN cat ./lib/.env >> /code/.env

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Expose the application
CMD ["uvicorn", "services_api:app", "--port", "9212", "--host", "0.0.0.0", "--reload"]

# Optional: Sleep for debugging purposes (remove or adjust as needed)
