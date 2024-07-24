import logging

import aiofiles
from fastapi import APIRouter, Depends, Form, HTTPException, Security, UploadFile
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

from goosebit.auth import authenticate_session, validate_user_permissions
from goosebit.models import Firmware
from goosebit.permissions import Permissions
from goosebit.settings import UPDATES_DIR
from goosebit.ui.templates import templates
from goosebit.updater.misc import parse_firmware_filename, sha1_hash_file

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui", dependencies=[Depends(authenticate_session)], include_in_schema=False
)


@router.get("/")
async def ui_root(request: Request):
    return RedirectResponse(request.url_for("home_ui"))


@router.get(
    "/firmware",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.FIRMWARE.READ])
    ],
)
async def firmware_ui(request: Request):
    return templates.TemplateResponse(
        "firmware.html", context={"request": request, "title": "Firmware"}
    )


@router.post(
    "/upload",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.FIRMWARE.WRITE])
    ],
)
async def upload_update(
    _: Request,
    chunk: UploadFile = Form(...),
    init: bool = Form(...),
    done: bool = Form(...),
    filename: str = Form(...),
):
    logging.info(f"upload_update, {filename}")

    try:
        model, revision, version = parse_firmware_filename(filename)
    except ValueError:
        raise HTTPException(400, detail="Could not parse file data, invalid filename.")

    file = UPDATES_DIR.joinpath(filename)
    tmp_file = file.with_suffix(".tmp")
    contents = await chunk.read()
    if init:
        file.unlink(missing_ok=True)

    async with aiofiles.open(tmp_file, mode="ab") as f:
        await f.write(contents)

    if done:
        result = tmp_file.replace(file)

        await Firmware.create(
            file=filename,
            sha1=sha1_hash_file(result),
            size=result.stat().st_size,
            hw_model=model,
            hw_revision=revision,
            version=version,
        )


@router.get(
    "/home",
    dependencies=[Security(validate_user_permissions, scopes=[Permissions.HOME.READ])],
)
async def home_ui(request: Request):
    return templates.TemplateResponse(
        "index.html", context={"request": request, "title": "Home"}
    )


@router.get(
    "/devices",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.DEVICE.READ])
    ],
)
async def devices_ui(request: Request):
    return templates.TemplateResponse(
        "devices.html", context={"request": request, "title": "Devices"}
    )


@router.get(
    "/rollouts",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.ROLLOUT.READ])
    ],
)
async def rollouts_ui(request: Request):
    return templates.TemplateResponse(
        "rollouts.html", context={"request": request, "title": "Rollouts"}
    )


@router.get(
    "/logs/{dev_id}",
    dependencies=[
        Security(validate_user_permissions, scopes=[Permissions.DEVICE.READ])
    ],
)
async def logs_ui(request: Request, dev_id: str):
    return templates.TemplateResponse(
        "logs.html", context={"request": request, "title": "Log", "device": dev_id}
    )
