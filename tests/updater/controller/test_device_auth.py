import pytest
import pytest_asyncio
from fastapi.requests import Request
from httpx import ASGITransport, AsyncClient
from tortoise.contrib.fastapi import RegisterTortoise

import goosebit
from conftest import TORTOISE_CONF
from goosebit import app
from goosebit.settings.schema import DeviceAuthMode


async def _api_device_get(device_auth_async_client, dev_id):
    response = await device_auth_async_client.get("/api/v1/devices")
    assert response.status_code == 200
    devices = response.json()["devices"]
    return next(d for d in devices if d["uuid"] == dev_id)


async def _api_device_update(device_auth_async_client, device, update_attribute, update_value):
    response = await device_auth_async_client.patch(
        f"/ui/bff/devices",
        json={"devices": [f"{device.uuid}"], update_attribute: update_value},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
class TestDeviceAuth:
    config = goosebit.settings.config

    @pytest_asyncio.fixture(scope="class")
    async def device_auth_async_client(self, device_auth_test_app):
        async with AsyncClient(
            transport=ASGITransport(app=device_auth_test_app), base_url="http://test", follow_redirects=True
        ) as client:
            login_data = {"username": "admin@goosebit.local", "password": "admin"}
            response = await client.post("/login", data=login_data, follow_redirects=True)
            assert response.status_code == 200

            data = response.json()
            client.cookies.set("session_id", data["access_token"])

            yield client

    @pytest_asyncio.fixture(scope="class")
    async def device_auth_test_app(self):
        async with RegisterTortoise(
            app=app,
            config=TORTOISE_CONF,
        ):

            @app.middleware("http")
            async def attach_config(request: Request, call_next):
                request.scope["config"] = self.config
                return await call_next(request)

            yield app

    async def test_poll_strict_with_no_auth_device_with_no_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_no_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.STRICT

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 401

    async def test_poll_strict_with_no_auth_device_with_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.STRICT

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 401

    async def test_poll_strict_with_auth_device_with_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.STRICT

        response = await device_auth_async_client.get(
            f"/ddi/controller/v1/{device.uuid}", headers={"Authorization": f"TargetToken {device.auth_token}"}
        )
        assert response.status_code == 200

    async def test_poll_lax_with_no_auth_device_with_no_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_no_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.LAX

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 200

    async def test_poll_lax_with_no_auth_device_with_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.LAX

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 401

    async def test_poll_lax_with_auth_device_with_auth(self, device_auth_test_app, device_auth_async_client, test_data):
        device = test_data["device_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.LAX

        response = await device_auth_async_client.get(
            f"/ddi/controller/v1/{device.uuid}", headers={"Authorization": f"TargetToken {device.auth_token}"}
        )
        assert response.status_code == 200

    async def test_poll_setup_with_no_auth(self, device_auth_test_app, device_auth_async_client, test_data):
        device = test_data["device_no_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.SETUP

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 200

        # device should not have changed
        device_api = await _api_device_get(device_auth_async_client, device.uuid)
        assert device_api["auth_token"] is None

    async def test_poll_setup_with_auth_add_device_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_no_authentication"]
        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.SETUP

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 200

        token = "testing123"
        await device_auth_async_client.get(
            f"/ddi/controller/v1/{device.uuid}", headers={"Authorization": f"TargetToken {token}"}
        )

        device_api = await _api_device_get(device_auth_async_client, device.uuid)
        assert device_api["auth_token"] == token

        await _api_device_update(device_auth_async_client, device, "auth_token", None)

    async def test_poll_setup_with_auth_update_device_auth(
        self, device_auth_test_app, device_auth_async_client, test_data
    ):
        device = test_data["device_authentication"]
        old_token = device.auth_token

        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.SETUP

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 200

        token = "testing123"
        await device_auth_async_client.get(
            f"/ddi/controller/v1/{device.uuid}", headers={"Authorization": f"TargetToken {token}"}
        )

        device_api = await _api_device_get(device_auth_async_client, device.uuid)
        assert device_api["auth_token"] == token

        await _api_device_update(device_auth_async_client, device, "auth_token", old_token)

    async def test_poll_setup_with_no_auth_no_change(self, device_auth_test_app, device_auth_async_client, test_data):
        device = test_data["device_authentication"]

        self.config.device_auth.enable = True
        self.config.device_auth.mode = DeviceAuthMode.SETUP

        response = await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")
        assert response.status_code == 200

        await device_auth_async_client.get(f"/ddi/controller/v1/{device.uuid}")

        device_api = await _api_device_get(device_auth_async_client, device.uuid)
        assert device_api["auth_token"] == device.auth_token
