"""
NDAI negotiation server client and dummy stub.

When --ndai is set, the game uses this client to:
- init/game/phase: kick off the server for a phase (wait for confirm)
- enter/game/phase/power_name: each power enters (wait for confirm)
- get_released_info/game/phase/round/power_name: each power gets released info per round

Set NDAI_SERVER_URL in env (e.g. http://127.0.0.1:8080) or defaults to that.
Run the dummy server with: python -m ai_diplomacy.ndai_server
"""

import asyncio
import json
import logging
import os
import random
from typing import Any, Dict

# All powers for stub released-info; normalize to uppercase for keys
STUB_POWERS = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]

STUB_RELEASED_MESSAGES = [
    "We should coordinate on the next move.",
    "I am open to a non-aggression pact this phase.",
    "My units will support your advance if you agree.",
    "Let us discuss the situation in the center.",
    "I have no hostile intentions toward you.",
    "Perhaps we can find a mutually beneficial arrangement.",
]

logger = logging.getLogger("ndai_server")

# Base URL for the NDAI server (no trailing slash)
def _base_url() -> str:
    return os.environ.get("NDAI_SERVER_URL", "http://127.0.0.1:8080")


async def init_game_phase(phase: str) -> bool:
    """Call local_server/init/game/phase; wait for confirm. Returns True on success or on connection error (dummy mode)."""
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed; NDAI client will use dummy responses. pip install httpx")
        return True
    base = _base_url().rstrip("/")
    url = f"{base}/local_server/init/game/phase"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json={"phase": phase})
            r.raise_for_status()
            data = r.json() if r.content else {}
            if data.get("status") in ("ok", "confirm", "confirmed") or r.status_code == 200:
                logger.info(f"NDAI init game phase confirmed for {phase}")
                return True
            logger.warning(f"NDAI init returned unexpected response: {data}")
            return True  # proceed anyway in dummy mode
    except Exception as e:
        logger.warning(f"NDAI init_game_phase failed (server may be down): {e}. Proceeding as dummy.")
        return True


async def enter_game_phase(phase: str, power_name: str) -> bool:
    """Call enter/game/phase/power_name; wait for confirm. Returns True on success or on connection error (dummy mode)."""
    try:
        import httpx
    except ImportError:
        return True
    base = _base_url().rstrip("/")
    url = f"{base}/enter/game/phase/{power_name}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json={"phase": phase})
            r.raise_for_status()
            data = r.json() if r.content else {}
            if data.get("status") in ("ok", "confirm", "confirmed") or r.status_code == 200:
                logger.info(f"NDAI enter confirmed for {power_name} in {phase}")
                return True
            logger.warning(f"NDAI enter returned unexpected response: {data}")
            return True
    except Exception as e:
        logger.warning(f"NDAI enter_game_phase failed for {power_name}: {e}. Proceeding as dummy.")
        return True


async def get_released_info(phase: str, round_num: int, power_name: str) -> Dict[str, str]:
    """
    Call get_released_info/game/phase/round/power_name; wait for response.
    Returns a dict mapping other_power -> released info string, e.g. {"RUSSIA": "...", "ITALY": "..."}.
    On connection error returns {} (dummy mode).
    """
    try:
        import httpx
    except ImportError:
        return {}
    base = _base_url().rstrip("/")
    url = f"{base}/get_released_info/game/{phase}/{round_num}/{power_name}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json() if r.content else {}
            # Accept {"released_info": {"RUSSIA": "...", ...}} or direct {"RUSSIA": "...", ...}
            if "released_info" in data and isinstance(data["released_info"], dict):
                return data["released_info"]
            if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
                return data
            return {}
    except Exception as e:
        logger.warning(f"NDAI get_released_info failed for {power_name}: {e}. Using empty released info.")
        return {}


# --- Dummy stub server (run with: python -m ai_diplomacy.ndai_server) ---

def _run_stub_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    class StubHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            try:
                data = json.loads(body.decode()) if body else {}
            except Exception:
                data = {}
            if self.path == "/local_server/init/game/phase":
                phase = data.get("phase", "unknown")
                logger.info(f"Stub: init game phase {phase}")
                response = {"status": "ok", "message": "confirmed"}
            elif self.path.startswith("/enter/game/phase/"):
                power_name = self.path.split("/")[-1]
                logger.info(f"Stub: enter {power_name}")
                response = {"status": "ok", "message": "confirmed"}
            else:
                response = {"status": "ok"}
            self._send_json(200, response)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 5 and parts[0] == "get_released_info" and parts[1] == "game":
                # get_released_info/game/phase/round/power_name
                phase = parts[2]
                round_num = parts[3]
                power_name = parts[4].upper()
                logger.info(f"Stub: get_released_info for {power_name} phase {phase} round {round_num}")
                # Return random released info from other powers
                others = [p for p in STUB_POWERS if p != power_name]
                num_released = random.randint(1, min(3, len(others)))
                chosen = random.sample(others, num_released)
                released_info = {
                    p: random.choice(STUB_RELEASED_MESSAGES) + f" (phase {phase}, round {round_num})"
                    for p in chosen
                }
                logger.info(f"Stub: returning released_info for {power_name}: {released_info}")
                response = {"released_info": released_info}
            else:
                response = {}
            self._send_json(200, response)

        def _send_json(self, code, obj):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            raw = json.dumps(obj).encode()
            self.send_header("Content-Length", len(raw))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format, *args):
            pass  # suppress default request logging

    port = int(os.environ.get("NDAI_STUB_PORT", "8080"))
    logger.info(f"NDAI stub server starting on port {port}")
    server = HTTPServer(("0.0.0.0", port), StubHandler)
    server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _run_stub_server()
