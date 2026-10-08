FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py auth.py drive_files.py index.html login.html yango_logo.png ./
ENV HOST=0.0.0.0 PORT=8765
EXPOSE 8765
CMD ["python", "app.py"]
