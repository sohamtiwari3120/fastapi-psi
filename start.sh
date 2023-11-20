cd /usr0/home/sohamdit/fastapi-psi/
source venv/bin/activate
# python fastapi_server.py
uvicorn fastapi_server:app --workers 4 --port 8081 --host 0.0.0.0