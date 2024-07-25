import logging
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from tortoise import Tortoise
from tortoise.contrib.fastapi import RegisterTortoise

from goosebit import app

# Configure logging
logging.basicConfig(level=logging.INFO)

TORTOISE_CONF = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "models": {
            "models": ["goosebit.models", "aerich.models"],
        },
    },
}


@pytest_asyncio.fixture(scope="module")
async def test_app():
    async with RegisterTortoise(
        app=app,
        config=TORTOISE_CONF,
        generate_schemas=True,
        add_exception_handlers=True,
        _create_db=True,
    ):
        yield app


@pytest_asyncio.fixture(scope="module")
async def async_client(test_app):
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def db():
    await Tortoise.init(config=TORTOISE_CONF)
    await Tortoise.generate_schemas()
    yield
    await Tortoise._drop_databases()
    await Tortoise.close_connections()


@pytest_asyncio.fixture(scope="function")
async def test_data(db, monkeypatch):
    # Initialize the data
    from goosebit.models import Device, Firmware, Rollout  # Import your models here

    device_default = await Device.create(uuid="device1", last_state="registered")
    firmware_default = await Firmware.create(
        version="1.0.0", sha1="dummy", size=1200, file="firmware1"
    )
    rollout_default = await Rollout.create(firmware_id=firmware_default.id)

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(
            "goosebit.updater.controller.v1.routes.UPDATES_DIR", Path(temp_dir)
        )

        temp_file_path = os.path.join(temp_dir, firmware_default.file)
        with open(temp_file_path, "w") as temp_file:
            temp_file.write("Hello, World!")

        yield dict(
            device_default=device_default,
            firmware_default=firmware_default,
            rollout_default=rollout_default,
        )
