from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import FileResponse

from goosebit.models import Firmware
from goosebit.settings import UPDATES_DIR

router = APIRouter(prefix="/v1")


@router.get("/{dev_id}/{firmware_id}")
async def download_file(request: Request, tenant: str, dev_id: str, firmware_id: int):
    firmware = await Firmware.get_or_none(id=firmware_id)
    if firmware:
        filename = UPDATES_DIR.joinpath(firmware.file)
        return FileResponse(filename, media_type="application/octet-stream")
