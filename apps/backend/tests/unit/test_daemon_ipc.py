
import asyncio
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from v2m.daemon import Daemon
from v2m.client import send_command, SOCKET_PATH
from v2m.core.ipc_protocol import MAX_MESSAGE_SIZE

@pytest.fixture
def mock_daemon(monkeypatch, tmp_path):
    # Mock socket path
    socket_path = tmp_path / "v2m.sock"
    monkeypatch.setattr("v2m.daemon.SOCKET_PATH", str(socket_path))
    monkeypatch.setattr("v2m.client.SOCKET_PATH", str(socket_path))

    # Mock container and command bus
    mock_bus = AsyncMock()
    mock_container = MagicMock()
    mock_container.get_command_bus.return_value = mock_bus

    # Patch dependencies in daemon.py
    monkeypatch.setattr("v2m.daemon.container", mock_container)

    # Patch cleaning methods to avoid side effects
    monkeypatch.setattr(Daemon, "_cleanup_orphaned_processes", lambda self: None)
    monkeypatch.setattr(Daemon, "_cleanup_resources", lambda self: None)

    # Patch sys.exit to avoid killing the test runner
    monkeypatch.setattr(sys, "exit", lambda code: None)

    # Create daemon instance
    daemon = Daemon()
    daemon.socket_path = socket_path # Update instance socket path
    return daemon, mock_bus

@pytest.mark.asyncio
async def test_large_payload_truncation(mock_daemon):
    """
    Test that large payloads are correctly received with the fix.
    Verifies the length-prefix framing protocol handles payloads >4KB.
    """
    daemon, mock_bus = mock_daemon

    # Start server in background task
    server_task = asyncio.create_task(daemon.start_server())

    # Give server time to start
    await asyncio.sleep(0.1)

    # Create a large payload > 4096 bytes
    large_text = "A" * 5000
    command = f"PROCESS_TEXT {large_text}"

    # Send command
    response = await send_command(command)

    # Stop server
    daemon.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    # Verify dispatch
    assert mock_bus.dispatch.called
    args, _ = mock_bus.dispatch.call_args
    cmd_obj = args[0]

    # Check if text is fully received
    # The command parser splits "PROCESS_TEXT <text>"
    # so cmd_obj.text should be the payload
    assert len(cmd_obj.text) == 5000, f"Payload truncated! Expected 5000, got {len(cmd_obj.text)}"

@pytest.mark.asyncio
async def test_ping_pong_symmetric_protocol(mock_daemon):
    """
    Test that PING/PONG works with symmetric framing protocol.
    Both request and response should use 4-byte length headers.
    """
    daemon, mock_bus = mock_daemon

    # Start server in background task
    server_task = asyncio.create_task(daemon.start_server())
    await asyncio.sleep(0.1)

    # Send PING command
    response = await send_command("PING")

    # Stop server
    daemon.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    # Verify response
    assert response == "PONG", f"Expected 'PONG', got '{response}'"

@pytest.mark.asyncio
async def test_oversized_message_rejection(mock_daemon):
    """
    Test that messages exceeding MAX_MESSAGE_SIZE are rejected.
    This prevents memory exhaustion attacks.
    """
    daemon, mock_bus = mock_daemon

    # Start server in background task
    server_task = asyncio.create_task(daemon.start_server())
    await asyncio.sleep(0.1)

    # Create a payload that exceeds MAX_MESSAGE_SIZE
    # We'll manually create the framed message to bypass client validation
    reader, writer = await asyncio.open_unix_connection(str(daemon.socket_path))
    
    # Send a header claiming the message is larger than MAX_MESSAGE_SIZE
    oversized_length = MAX_MESSAGE_SIZE + 1
    writer.write(oversized_length.to_bytes(4, byteorder="big"))
    await writer.drain()
    
    # Read response using the framing protocol
    try:
        response_header = await reader.readexactly(4)
        response_length = int.from_bytes(response_header, byteorder="big")
        response_data = await reader.readexactly(response_length)
        response = response_data.decode("utf-8")
    except asyncio.IncompleteReadError:
        response = "Connection closed"
    
    writer.close()
    await writer.wait_closed()

    # Stop server
    daemon.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    # Verify error response
    assert "ERROR" in response or "too large" in response.lower(), \
        f"Expected error for oversized message, got: {response}"

