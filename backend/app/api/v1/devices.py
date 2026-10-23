"""Payment Device API endpoints"""
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.payment_device_service import PaymentDeviceService
from app.services.biometric_service import BiometricService
from app.services.audit_service import AuditService
from app.schemas.payment_device import (
    PaymentDeviceCreate, PaymentDeviceUpdate, PaymentDeviceResponse, PaymentDeviceListResponse,
    DevicePairRequest, DeviceHeartbeatRequest, PaymentDeviceRegisterResponse
)
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, DeviceError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_device_service(db: AsyncSession = Depends(get_db)) -> "PaymentDeviceService":
    from app.services.payment_device_service import PaymentDeviceService
    return PaymentDeviceService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/devices/register",
    response_model=PaymentDeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Devices", "Admin"]
)
async def register_device(
    request: Request,
    device_data: PaymentDeviceCreate,
    device_service: PaymentDeviceService = Depends(get_device_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Register a new payment device (admin only).
    Returns device_id and device_key (only shown once!).
    """
    device, device_key = await device_service.register_device(device_data)

    await audit_service.log_device_event(
        "device_registered",
        device.id,
        request_id,
        metadata={"device_name": device.device_name}
    )

    return PaymentDeviceRegisterResponse(
        device_id=device.id,
        device_key=device_key,
        message="Device registered successfully. Save the device_key securely!"
    )


@router.post(
    "/devices/authenticate",
    response_model=PaymentDeviceResponse,
    tags=["Devices"]
)
async def authenticate_device(
    request: Request,
    auth_data: DevicePairRequest,
    device_service: PaymentDeviceService = Depends(get_device_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Authenticate device with device_id and device_key"""
    try:
        device = await device_service.authenticate_device(auth_data.device_id, auth_data.device_key)
    except DeviceError as e:
        await audit_service.log_device_event(
            "device_auth_failed",
            auth_data.device_id,
            request_id,
            metadata={"error": e.message}
        )
        raise

    await audit_service.log_device_event(
        "device_authenticated",
        device.id,
        request_id
    )

    return PaymentDeviceResponse.model_validate(device)


@router.post(
    "/devices/{device_id}/heartbeat",
    response_model=PaymentDeviceResponse,
    tags=["Devices"]
)
async def device_heartbeat(
    device_id: UUID,
    heartbeat_data: DeviceHeartbeatRequest,
    request: Request,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """Device heartbeat to update connection status"""
    device = await device_service.device_heartbeat(device_id, heartbeat_data.ip_address, heartbeat_data.metadata)
    return PaymentDeviceResponse.model_validate(device)


@router.post(
    "/devices/{device_id}/pair",
    response_model=PaymentDeviceResponse,
    tags=["Devices"]
)
async def pair_device(
    device_id: UUID,
    request: Request,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """Pair a device with a business"""
    paired_by = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
    device = await device_service.pair_device(device_id, paired_by)
    return PaymentDeviceResponse.model_validate(device)


@router.post(
    "/devices/{device_id}/unpair",
    response_model=PaymentDeviceResponse,
    tags=["Devices"]
)
async def unpair_device(
    device_id: UUID,
    request: Request,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """Unpair a device"""
    device = await device_service.unpair_device(device_id)
    return PaymentDeviceResponse.model_validate(device)


@router.post(
    "/devices/{device_id}/revoke",
    response_model=PaymentDeviceResponse,
    tags=["Devices", "Admin"]
)
async def revoke_device(
    device_id: UUID,
    request: Request,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """Revoke a device"""
    device = await device_service.revoke_device(device_id)
    return PaymentDeviceResponse.model_validate(device)


@router.get("/devices", response_model=PaymentDeviceListResponse, tags=["Devices"])
async def list_devices(
    request: Request,
    business_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: Optional[str] = None,
    pairing_status: Optional[str] = None,
    connection_status: Optional[str] = None,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """List devices with pagination"""
    devices, total = await device_service.list_devices(
        business_id, page, page_size,
        branch_id=branch_id, pairing_status=pairing_status, connection_status=connection_status
    )
    return PaymentDeviceListResponse(
        devices=devices,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/devices/{device_id}", response_model=PaymentDeviceResponse, tags=["Devices"])
async def get_device(
    device_id: UUID,
    request: Request,
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """Get device information"""
    device = await device_service.get_device(device_id)
    if not device:
        raise NotFoundError("Device not found")
    return PaymentDeviceResponse.model_validate(device)


# In-memory storage for latest ESP32 hardware scans
latest_device_scans: Dict[str, Any] = {}


class ESP32CaptureRequest(BaseModel):
    device_url: Optional[str] = "http://192.168.1.100"
    device_id: Optional[UUID] = None


@router.get("/devices/esp32/stream", tags=["Devices", "ESP32"])
async def stream_esp32_video(
    device_url: Optional[str] = "http://192.168.1.100",
    device_id: Optional[UUID] = None,
    device_service: PaymentDeviceService = Depends(get_device_service)
):
    """
    Real-Time live MJPEG video stream proxy for physical ESP32 Near-Infrared camera.
    Proxies live frames from ESP32 directly to the frontend HUD viewfinder.
    """
    import httpx
    import asyncio
    import cv2
    import numpy as np

    target_url = device_url.strip() if device_url else "http://192.168.1.100"
    if not target_url and device_id:
        device = await device_service.get_device(device_id)
        if device and device.ip_address:
            target_url = f"http://{device.ip_address}"

    target_url = target_url.rstrip("/")

    def make_standby_frame(msg: str) -> bytes:
        frame = np.zeros((320, 320, 3), dtype=np.uint8)
        frame[:] = (20, 16, 12)
        cv2.circle(frame, (160, 160), 100, (212, 245, 0), 1)
        cv2.circle(frame, (160, 160), 50, (120, 180, 80), 1)
        cv2.line(frame, (160, 40), (160, 280), (80, 120, 50), 1)
        cv2.line(frame, (40, 160), (280, 160), (80, 120, 50), 1)
        cv2.putText(frame, "ESP32 NIR LIVE FEED", (45, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 245, 212), 1)
        cv2.putText(frame, msg, (20, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1)
        _, enc = cv2.imencode(".jpg", frame)
        return enc.tobytes()

    async def frame_generator():
        capture_url = f"{target_url}/capture" if not target_url.endswith("/capture") else target_url
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                while True:
                    try:
                        r = await client.get(capture_url)
                        if r.status_code == 200 and len(r.content) > 1000:
                            frame_bytes = r.content
                        else:
                            frame_bytes = make_standby_frame("ESP32 STANDBY (AWAITING PALM)")
                    except Exception:
                        frame_bytes = make_standby_frame(f"CONNECTING TO {target_url}...")

                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )
                    await asyncio.sleep(0.1)
        except (asyncio.CancelledError, GeneratorExit):
            return

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/devices/esp32/capture", tags=["Devices", "ESP32"])
async def trigger_esp32_capture(
    request: Request,
    capture_req: ESP32CaptureRequest,
    db: AsyncSession = Depends(get_db),
    device_service: PaymentDeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """
    Trigger palm scan capture on physical ESP32 device.
    Fetches the JPEG image from the ESP32 endpoint, runs biometric identification,
    and returns both the image (base64) and match result.
    """
    import httpx
    import base64

    target_url = capture_req.device_url.strip() if capture_req.device_url else None
    if not target_url and capture_req.device_id:
        device = await device_service.get_device(capture_req.device_id)
        if device and device.ip_address:
            target_url = f"http://{device.ip_address}"

    if not target_url:
        target_url = "http://192.168.1.100"

    target_url = target_url.rstrip("/")
    if not target_url.endswith("/capture") and not target_url.endswith(".jpg"):
        target_endpoint = f"{target_url}/capture"
    else:
        target_endpoint = target_url

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(target_endpoint)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "application/json" in ct:
                    json_data = resp.json()
                    image_b64 = json_data.get("image") or json_data.get("image_base64")
                else:
                    image_b64 = base64.b64encode(resp.content).decode("utf-8")

                # Run biometric identification on captured image
                biometric_service = BiometricService(db)
                matched, user_id, similarity, reason = await biometric_service.identify(image_b64)

                dev_key = str(capture_req.device_id) if capture_req.device_id else "default"
                scan_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "image": image_b64,
                    "matched": matched,
                    "user_id": str(user_id) if user_id else None,
                    "similarity": similarity,
                    "device_url": target_endpoint,
                }
                latest_device_scans[dev_key] = scan_record

                return {
                    "success": True,
                    "image": image_b64,
                    "matched": matched,
                    "user_id": user_id,
                    "similarity": similarity,
                    "reason": reason,
                    "device_url": target_endpoint,
                    "request_id": request_id
                }
            else:
                return {
                    "success": False,
                    "error": f"ESP32 returned HTTP {resp.status_code}",
                    "device_url": target_endpoint
                }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Could not reach ESP32 at {target_endpoint}: {str(exc)}",
            "device_url": target_endpoint
        }


@router.post("/devices/{device_id}/upload-scan", tags=["Devices", "ESP32"])
async def esp32_upload_scan(
    device_id: UUID,
    request: Request,
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
):
    """
    Direct upload endpoint for ESP32 hardware to send palm scans over WiFi.
    Supports both multipart/form-data ('image' field) and raw binary image/jpeg payloads.
    """
    import base64
    content = None
    if image is not None:
        content = await image.read()
    else:
        body = await request.body()
        if body and len(body) > 100:
            content = body

    if not content:
        raise HTTPException(status_code=400, detail="No image payload received from ESP32")

    image_b64 = base64.b64encode(content).decode("utf-8")

    biometric_service = BiometricService(db)
    matched, user_id, similarity, reason = await biometric_service.identify(image_b64)

    scan_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "image": image_b64,
        "matched": matched,
        "user_id": str(user_id) if user_id else None,
        "similarity": similarity,
        "source": "esp32_hardware"
    }
    latest_device_scans[str(device_id)] = scan_record

    return {
        "success": True,
        "matched": matched,
        "user_id": user_id,
        "similarity": similarity,
        "reason": reason,
        "request_id": request_id
    }


@router.get("/devices/{device_id}/latest-scan", tags=["Devices", "ESP32"])
async def get_latest_esp32_scan(
    device_id: UUID,
    since: Optional[str] = None
):
    """
    Retrieve the most recent scan sent by or captured from this ESP32 device.
    Allows real-time auto-detection when a palm is placed on the physical device.
    """
    dev_key = str(device_id)
    scan = latest_device_scans.get(dev_key)
    if not scan:
        return {"has_scan": False, "scan": None}

    if since and scan.get("timestamp") <= since:
        return {"has_scan": False, "scan": None}

    return {"has_scan": True, "scan": scan}