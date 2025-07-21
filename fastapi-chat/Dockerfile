FROM python:3.11-slim
WORKDIR /app
COPY . /app
EXPOSE 80
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi==0.110.2 uvicorn[standard]==0.29.0 jinja2 PyJWT passlib[bcrypt] python-multipart pymysql cryptography python-dotenv redis
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
