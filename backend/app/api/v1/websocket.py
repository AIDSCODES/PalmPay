"""WebSocket endpoints for real-time device communication"""
import json
import logging
from typing import Dict, Set
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models.payment_device import PaymentDevice, ConnectionStatus
from app.core.security import verify_device_key
from app.services.payment_request_service import PaymentRequestService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for devices"""

    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        self.device_keys: Dict[WebSocket, UUID] = {}  # WebSocket -> device_id

    async def connect(self, websocket: WebSocket, device_id: UUID, device_key: str, db: AsyncSession):
        """Authenticate and connect a device"""
        # Authenticate device
        from app.db.models.payment_device import PaymentDevice
        from app.core.security import verify_device_key

        stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not found")
            return False

        if not verify_device_key(device_key, device.device_key_hash):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid device key")
            return False

        if device.pairing_status != "PAIRED":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not paired")
            return False

        # Accept connection
        await websocket.accept()

        # Store connection
        if device.id not in self.active_connections:
            self.active_connections[device.id] = set()
        self.active_connections[device.id].add(websocket)
        self.device_keys[websocket] = device.id

        # Update device connection status
        from app.db.models.payment_device import PaymentDevice, ConnectionStatus
        stmt = select(PaymentDevice).where(PaymentDevice.id == device.id)
        result = await db.execute(stmt)
        device_obj = result.scalar_one_or_none()
        if device_obj:
            device_obj.connection_status = "ONLINE"
            device_obj.last_seen = datetime.utcnow()
            await db.commit()

        logger.info(f"Device {device_id} connected via WebSocket")
        return True

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        device_id = self.device_keys.get(websocket)
        if device_id and device_id in self.active_connections:
            self.active_connections[device_id].discard(websocket)
            if not self.active_connections[device_id]:
                del self.active_connections[device_id]
        self.device_keys.pop(websocket, None)

    async def send_to_device(self, device_id: UUID, message: dict):
        """Send message to all connections for a device"""
        if device_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[device_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add(websocket)

            # Clean up disconnected
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast_to_business(self, business_id: str, message: dict, db: AsyncSession):
        """Broadcast message to all devices in a business"""
        from app.db.models.payment_device import PaymentDevice
        stmt = select(PaymentDevice).where(PaymentDevice.business_id == UUID(business_id))
        result = await db.execute(stmt)

        for device in result.scalars().all():
            await self.send_to_device(device.id, message)


manager = ConnectionManager()


@router.websocket("/ws/device/{device_id}")
async def device_websocket(
    websocket: WebSocket,
    device_id: UUID,
    device_key: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for device communication"""
    from app.db.models.payment_device import PaymentDevice
    from app.core.security import verify_device_key

    # Authenticate device
    stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if not device:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not found")
        return

    if not verify_device_key(device_key, device.device_key_hash):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid device key")
        return

    if device.pairing_status != "PAIRED":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not paired")
        return

    # Accept connection
    await websocket.accept()

    # Update connection status
    stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
    result = await db.execute(stmt)
    device_obj = result.scalar_one_or_none()
    if device_obj:
        device_obj.connection_status = "ONLINE"
        device_obj.last_seen = datetime.utcnow()
        await db.commit()

    # Store connection
    if device.id not in manager.active_connections:
        manager.active_connections[device.id] = set()
    manager.active_connections[device.id].add(websocket)
    manager.device_keys[websocket] = device.id

    logger.info(f"Device {device_id} connected via WebSocket")

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "device_id": str(device_id),
            "message": "Connected to PalmPay backend"
        })

        # Listen for messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "heartbeat":
                # Update last seen
                from app.db.models.payment_device import PaymentDevice, ConnectionStatus
                stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
                result = await db.execute(stmt)
                device_obj = result.scalar_one_or_none()
                if device_obj:
                    device_obj.connection_status = "ONLINE"
                    device_obj.last_seen = datetime.utcnow()
                    await db.commit()

                await websocket.send_json({"type": "heartbeat_ack"})

            elif message_type == "acknowledge":
                # Device acknowledges payment request
                request_id = data.get("request_id")
                if request_id:
                    payment_request_service = PaymentRequestService(db)
                    try:
                        await payment_request_service.device_acknowledge(UUID(request_id), device_id)
                        await websocket.send_json({
                            "type": "acknowledge_result",
                            "request_id": request_id,
                            "success": True
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "acknowledge_result",
                            "request_id": request_id,
                            "success": False,
                            "error": str(e)
                        })

            elif message_type == "customer_identified":
                # Customer identified via biometric
                request_id = data.get("request_id")
                customer_user_id = data.get("customer_user_id")
                biometric_verified = data.get("biometric_verified", True)

                if request_id and customer_user_id:
                    payment_request_service = PaymentRequestService(db)
                    try:
                        await payment_request_service.customer_identified(
                            UUID(request_id), UUID(customer_user_id), biometric_verified
                        )
                        await websocket.send_json({
                            "type": "customer_identified_result",
                            "request_id": request_id,
                            "success": True
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "customer_identified_result",
                            "request_id": request_id,
                            "success": False,
                            "error": str(e)
                        })

            elif message_type == "payment_result":
                # Device sends payment result (for external payment providers)
                request_id = data.get("request_id")
                success = data.get("success", False)
                transaction_id = data.get("transaction_id")
                failure_reason = data.get("failure_reason")

                if request_id:
                    # Store result and update payment request
                    pass  # Implementation depends on specific payment provider

    except WebSocketDisconnect:
        logger.info(f"Device {device_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id}: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
    finally:
        manager.disconnect(websocket)

        # Update connection status to OFFLINE
        from app.db.models.payment_device import PaymentDevice, ConnectionStatus
        stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
        result = await db.execute(stmt)
        device_obj = result.scalar_one_or_none()
        if device_obj:
            device_obj.connection_status = "OFFLINE"
            await db.commit()

        logger.info(f"Device {device_id} disconnected")