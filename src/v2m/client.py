import asyncio
import sys
import argparse
from v2m.core.ipc_protocol import SOCKET_PATH, IPCCommand

async def send_command(command: str):
    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)

        writer.write(command.encode())
        await writer.drain()

        data = await reader.read(1024)
        response = data.decode()
        # print(f"Response: {response}")

        writer.close()
        await writer.wait_closed()
        return response
    except FileNotFoundError:
        print("Error: Daemon is not running. Start it with 'python -m v2m.daemon'", file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        print("Error: Connection refused. Daemon might be dead.", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Whisper Dictation Client")
    parser.add_argument("command", choices=[e.value for e in IPCCommand], help="Command to send to daemon")
    parser.add_argument("payload", nargs="*", help="Optional payload for the command")

    args = parser.parse_args()

    full_command = args.command
    if args.payload:
        full_command += " " + " ".join(args.payload)

    response = asyncio.run(send_command(full_command))
    print(response)

if __name__ == "__main__":
    main()
