@echo off
echo Starting Robo-Advisory Portfolio Dashboard...
echo.
echo Installing dependencies if needed...
pip install -r requirements.txt -q
echo.
echo Launching Streamlit server...
echo Dashboard will open at: http://localhost:8501
echo.
streamlit run app.py --server.port 8501 --server.headless true