import logging

from fastapi import APIRouter, status

from schemas import SyncTriggerResponse
from services.sync import is_sync_running, run_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger", include_in_schema=False)
@router.post(
    "/trigger/", response_model=SyncTriggerResponse, status_code=status.HTTP_200_OK
)
async def trigger_sync() -> SyncTriggerResponse:
    if is_sync_running():
        return SyncTriggerResponse(
            status="already_running",
            message="Sync is already in progress",
        )

    result = await run_sync()
    return SyncTriggerResponse(
        status="completed",
        message=f"Sync finished: {result}",
    )
