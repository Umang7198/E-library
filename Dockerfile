# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh



# Make port 5000 available to the world outside this container
EXPOSE 5000
ENTRYPOINT ["/app/entrypoint.sh"]

# Define environment variable
ENV FLASK_APP=app.py

# Run the shell script to initialize the database and start the server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
