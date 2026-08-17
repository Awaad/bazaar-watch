"""Development entry point.

Production runs uvicorn directly against `bazaarwatch.app:create_app`.
"""

from __future__ import annotations

import uvicorn

from bazaarwatch.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "bazaarwatch.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=settings.api_port,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    main()
