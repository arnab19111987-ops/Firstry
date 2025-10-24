FROM mcr.microsoft.com/vscode/devcontainers/python:latest

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Set up the working directory
WORKDIR /workspace

# Install any additional dependencies if needed
# RUN npm install -g <additional-packages> 

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose any ports if necessary
# EXPOSE <port-number>