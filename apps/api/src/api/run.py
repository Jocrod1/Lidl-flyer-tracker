"""Production entrypoint for the Render web service."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Run the API on Render's externally provided port."""
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
