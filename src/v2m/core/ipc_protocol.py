from enum import Enum

class IPCCommand(str, Enum):
    START_RECORDING = "START_RECORDING"
    STOP_RECORDING = "STOP_RECORDING"
    PROCESS_TEXT = "PROCESS_TEXT"
    PING = "PING"
    SHUTDOWN = "SHUTDOWN"

SOCKET_PATH = "/tmp/v2m.sock"
