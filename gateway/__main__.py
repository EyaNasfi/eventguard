"""python -m gateway   (inside the lab: the gateway container runs this)"""

import logging

import uvicorn

from gateway.settings import GatewaySettings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = GatewaySettings()
    uvicorn.run(
        "gateway.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
