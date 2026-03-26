"""Application entry point."""

import uvicorn
from keiz.config import settings


def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "keiz.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
