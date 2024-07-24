from fastapi import APIRouter, Security
from fastapi.requests import Request

from goosebit.auth import validate_user_permissions
from goosebit.models import Firmware
from goosebit.permissions import Permissions
from goosebit.settings import UPDATES_DIR

router = APIRouter(prefix="/firmware")


@router.get(
    "/all",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.FIRMWARE.READ])
    ],
)
async def firmware_get_all() -> list[dict]:
    firmware_list = await Firmware.all().order_by("-created_at")
    return [
        {
            "id": firmware.id,
            "name": firmware.file,
            "size": firmware.size,
            "version": firmware.version,
        }
        for firmware in firmware_list
    ]


@router.post(
    "/delete",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.FIRMWARE.DELETE])
    ],
)
async def firmware_delete(_: Request, firmware_id: int) -> dict:
    firmware = await Firmware.get_or_none(firmware_id=firmware_id)
    if firmware:
        file_path = UPDATES_DIR.joinpath(firmware.file)
        if file_path.exists():
            file_path.unlink()
            return {"success": True}

    return {"success": False}
