from __future__ import annotations

import uvicorn

from .config import settings


def main() -> None:
    from .app import create_app

    app = create_app(start_sim=True, start_collector=True)
    print(f"IndusMon dashboard → http://{settings.host}:{settings.port}/")
    print(f"OpenAPI docs       → http://{settings.host}:{settings.port}/docs")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
