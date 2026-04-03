FROM python:3.9

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default port
EXPOSE 7860

CMD ["python", "app.py"]
