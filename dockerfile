# Use official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /whatsapp-bot

# Copy the current directory contents into the container at /app
COPY . /whatsapp-bot

# Install any needed packages specified in requirements.txt
RUN pip3 install -r /whatsapp-bot/requirements.txt

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["python3", "main.py"]
