
import asyncio
import struct
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from v2m.daemon import Daemon
from v2m.client import send_command, SOCKET_PATH

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
