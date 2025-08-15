# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We also install git because py-solc-x may need it
RUN apt-get update && apt-get install -y git && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Command to run when the container launches
# This is just a placeholder; services will be run explicitly
CMD ["/bin/bash"]
