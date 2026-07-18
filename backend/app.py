from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
BACKEND_DIR = BASE_DIR / "backend"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "beijing_tdrive"

for path in [BASE_DIR, SRC_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backend.config import load_env_file
from backend.routes.ai import register_ai_routes
from backend.routes.api import register_api_routes
from backend.services.output_store import OutputStore

load_env_file(BACKEND_DIR / ".env")


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    output_dir = Path(os.environ.get("NIGHTSENSE_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)).resolve()
    store = OutputStore(output_dir)
    register_api_routes(app, store)
    register_ai_routes(app, store)
    return app


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
