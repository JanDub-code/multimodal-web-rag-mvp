cd /home/hans/Downloads/ASS_mvp_vision_extended/local-multimodal-mvp
source .venv/bin/activate
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
