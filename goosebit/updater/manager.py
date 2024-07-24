from __future__ import annotations

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable, Optional

from goosebit.models import Device, Firmware, Rollout, UpdateModeEnum
from goosebit.settings import POLL_TIME, POLL_TIME_UPDATING
from goosebit.telemetry import devices_count
from goosebit.updates.artifacts import FirmwareArtifact

logger = logging.getLogger(__name__)


class UpdateManager(ABC):
    def __init__(self, dev_id: str):
        self.dev_id = dev_id
        self.config_data = {}
        self.device = None
        self.force_update = False
        self.update_complete = False
        self.poll_time = POLL_TIME
        self.log_subscribers: list[Callable] = []

    async def get_device(self) -> Device | None:
        return

    async def save(self) -> None:
        return

    async def update_installed_firmware(self, firmware: Firmware) -> None:
        return

    async def update_hw_model(self, hw_model: str) -> None:
        return

    async def update_hw_revision(self, hw_revision: str) -> None:
        return

    async def update_device_state(self, state: str) -> None:
        return

    async def update_last_seen(self, last_seen: int) -> None:
        return

    async def update_last_ip(self, last_ip: str) -> None:
        return

    async def get_rollout(self) -> Optional[Rollout]:
        return None

    async def update_config_data(self, **kwargs):
        await self.update_hw_model(kwargs.get("hw_model") or "default")
        await self.update_hw_revision(kwargs.get("hw_revision") or "default")

        device = await self.get_device()
        if device.last_state == "unknown":
            await self.update_device_state("registered")
        await self.save()

        self.config_data.update(kwargs)

    @asynccontextmanager
    async def subscribe_log(self, callback: Callable):
        device = await self.get_device()
        self.log_subscribers.append(callback)
        await callback(device.last_log)
        try:
            yield
        except asyncio.CancelledError:
            pass
        finally:
            self.log_subscribers.remove(callback)

    @property
    def poll_seconds(self):
        time_obj = datetime.strptime(self.poll_time, "%H:%M:%S")
        return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

    async def publish_log(self, log_data: str | None):
        for cb in self.log_subscribers:
            await cb(log_data)

    @abstractmethod
    async def get_update_firmware(self) -> FirmwareArtifact: ...

    @abstractmethod
    async def get_update(self) -> tuple: ...

    @abstractmethod
    async def update_log(self, log_data: str) -> None: ...


class UnknownUpdateManager(UpdateManager):
    def __init__(self, dev_id: str):
        super().__init__(dev_id)
        self.poll_time = POLL_TIME_UPDATING

    async def get_update_firmware(self) -> Firmware:
        # TODO
        return None

    async def get_update(self) -> tuple:
        return "forced"

    async def update_log(self, log_data: str) -> None:
        return


class DeviceUpdateManager(UpdateManager):
    async def get_device(self) -> Device:
        if not self.device:
            self.device = (await Device.get_or_create(uuid=self.dev_id))[0]
        return self.device

    async def save(self) -> None:
        await self.device.save()

    async def update_installed_firmware(self, firmware: Firmware) -> None:
        device = await self.get_device()
        device.installed_firmware = firmware

    async def update_hw_model(self, hw_model: str) -> None:
        device = await self.get_device()
        device.hw_model = hw_model

    async def update_hw_revision(self, hw_revision: str) -> None:
        device = await self.get_device()
        device.hw_revision = hw_revision

    async def update_device_state(self, state: str) -> None:
        device = await self.get_device()
        device.last_state = state

    async def update_last_seen(self, last_seen: int) -> None:
        device = await self.get_device()
        device.last_seen = last_seen

    async def update_last_ip(self, last_ip: str) -> None:
        device = await self.get_device()
        if ":" in last_ip:
            device.last_ipv6 = last_ip
        else:
            device.last_ip = last_ip

    async def get_rollout(self) -> Optional[Rollout]:
        device = await self.get_device()

        if device.update_mode == UpdateModeEnum.ROLLOUT:
            return (
                await Rollout.filter(
                    firmware__hw_model=device.hw_model,
                    firmware__hw_revision=device.hw_revision,
                    feed=device.feed,
                    flavor=device.flavor,
                )
                .order_by("-created_at")
                .first()
            )

        return None

    async def get_update_firmware(self) -> Optional[Firmware]:
        device = await self.get_device()

        if device.update_mode == UpdateModeEnum.ROLLOUT:
            rollout = await self.get_rollout()
            if rollout and not rollout.paused:
                await rollout.fetch_related("firmware")
                return rollout.firmware

        if device.update_mode == UpdateModeEnum.ASSIGNED:
            await device.fetch_related("assigned_firmware")
            return device.assigned_firmware

        if device.update_mode == UpdateModeEnum.LATEST:
            # TODO
            return None

        return None

    async def get_update(self) -> tuple:
        device = await self.get_device()

        firmware = await self.get_update_firmware()
        if firmware is None:
            mode = "skip"
            self.poll_time = POLL_TIME
            logger.info(f"Skip: no update available, device={device.uuid}")

        elif device.installed_firmware == firmware and not self.force_update:
            mode = "skip"
            self.poll_time = POLL_TIME
            logger.info(f"Skip: device up-to-date, device={device.uuid}")

        elif device.last_state == "error" and not self.force_update:
            mode = "skip"
            self.poll_time = POLL_TIME
            logger.info(f"Skip: device in error state, device={device.uuid}")
        else:
            mode = "forced"
            self.poll_time = POLL_TIME_UPDATING
            logger.info(f"Forced: update available, device={device.uuid}")

            if self.update_complete:
                self.update_complete = False
                await self.clear_log()

        return mode, firmware

    async def update_log(self, log_data: str) -> None:
        if log_data is None:
            return
        device = await self.get_device()
        matches = re.findall(r"Downloaded (\d+)%", log_data)
        if matches:
            device.progress = matches[-1]
        if device.last_log is None:
            device.last_log = ""
        if log_data.startswith("Installing Update Chunk Artifacts."):
            await self.clear_log()
        if log_data == "All Chunks Installed.":
            self.force_update = False
            self.update_complete = True
        if not log_data == "Skipped Update.":
            device.last_log += f"{log_data}\n"
            await self.publish_log(f"{log_data}\n")
        await device.save()

    async def clear_log(self) -> None:
        device = await self.get_device()
        device.last_log = ""
        await device.save()
        await self.publish_log(None)


device_managers = {"unknown": UnknownUpdateManager("unknown")}


async def get_update_manager(dev_id: str) -> UpdateManager:
    global device_managers
    if device_managers.get(dev_id) is None:
        device_managers[dev_id] = DeviceUpdateManager(dev_id)
    devices_count.set(len(await Device.all()))
    return device_managers[dev_id]


def get_update_manager_sync(dev_id: str) -> UpdateManager:
    global device_managers
    if device_managers.get(dev_id) is None:
        device_managers[dev_id] = DeviceUpdateManager(dev_id)
    return device_managers[dev_id]


async def delete_device(dev_id: str) -> None:
    global device_managers
    try:
        updater = get_update_manager_sync(dev_id)
        await (await updater.get_device()).delete()
        del device_managers[dev_id]
    except KeyError:
        pass
