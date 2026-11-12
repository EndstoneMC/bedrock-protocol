"""Have a stock bedrock_server read library-encoded packets and write back its own bytes and JSON."""

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Json = Any
Place = tuple[tuple[str, int], ...]

CEREAL_FIRST = 3
CEREAL_ONLY = 5
MANUAL_ONLY = 0
FIRST_PORT = 40000
STARTED = "Server started."
START_TIMEOUT = 600
STOP_TIMEOUT = 60
TOKEN = re.compile(
    r'(?P<separator>[:,]?)(?:(?P<close>[}\]])|(?P<open>[{\[])|(?P<scalar>"(?:[^"\\]|\\.)*"'
    r"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null))"
)


@dataclass(frozen=True)
class Slots:
    write_with_mode: int
    write: int
    read: int
    serialization_mode: int
    to_string: int


@dataclass(frozen=True)
class Stream:
    view: int
    read_pointer: int
    overflowed: int
    buffer: int
    size: int


@dataclass(frozen=True)
class Build:
    """Where one bedrock_server keeps what the script calls, as file addresses and offsets."""

    version: str
    protocol: int
    create_packet: int
    default_constructors: dict[int, int]
    server_network_system: int
    reflection_ctx: int
    reflection_ctx_vtable: int
    read_only_binary_stream_vtable: int
    binary_stream_vtable: int
    stream: Stream
    slots: Slots
    result_ok: int
    run_events: int


BUILDS = {
    "689e1ee7e23646c06c3908ef08e1f9635793e2c582d0043a6861be71d94aa034": Build(
        version="1.26.40.8",
        protocol=2168,
        create_packet=0x85993B0,
        default_constructors={324: 0x7D121C0},
        server_network_system=0x84FB3E0,
        reflection_ctx=0x1E0,
        reflection_ctx_vtable=0xE280048,
        read_only_binary_stream_vtable=0xE83F4B0,
        binary_stream_vtable=0xE83E5E0,
        stream=Stream(view=0x20, read_pointer=0x30, overflowed=0x38, buffer=0x40, size=0x48),
        slots=Slots(write_with_mode=6, write=7, read=9, serialization_mode=13, to_string=15),
        result_ok=0x40,
        run_events=0x8597890,
    ),
}


def tokens(text: str) -> list[tuple[Json, Place]]:
    """Split BDS's JSON text, valid or not, into its scalars in order, each with the bracket and index at each depth."""
    found: list[tuple[Json, Place]] = []
    brackets = ["["]
    counts = [0]
    position = 0
    while position < len(text):
        match = TOKEN.match(text, position)
        if match is None:
            raise ValueError(f"BDS's JSON: no token at {text[position : position + 20]!r}")
        position = match.end()
        separator, close, opened, scalar = match.group("separator", "close", "open", "scalar")
        if close:
            if separator or len(brackets) == 1 or {"{": "}", "[": "]"}[brackets[-1]] != close:
                raise ValueError(f"BDS's JSON: {close!r} closes nothing at {match.start()}")
            brackets.pop()
            counts.pop()
            continue
        wanted = "" if counts[-1] == 0 else ":" if brackets[-1] == "{" and counts[-1] % 2 else ","
        if separator != wanted:
            raise ValueError(f"BDS's JSON: {separator!r} where rapidjson writes {wanted!r} at {match.start()}")
        counts[-1] += 1
        if opened:
            brackets.append(opened)
            counts.append(0)
        else:
            found.append((json.loads(scalar), tuple(zip(brackets, [count - 1 for count in counts], strict=True))))
    if len(brackets) != 1:
        raise ValueError("BDS's JSON: an object or array is left open")
    return found


def unmatched(shown: list[tuple[Json, Place]], printed: list[list[Json]]) -> str | None:
    """Describe the first scalar BDS's JSON and the case's printed list part on; only a name BDS gives goes unlisted."""
    shifts: dict[Place, int] = {}
    run: tuple[Place, int, int] = ((), 0, 0)
    position = 0
    for scalar, place in shown:
        outer, (bracket, index) = place[:-1], place[-1]
        entry = printed[position] if position < len(printed) else None
        running = entry is not None and len(entry) > 2 and outer == run[0]
        named = bracket == "{" and (index - shifts.get(outer, 0)) % 2 == 0 and isinstance(scalar, str) and not running
        if entry is not None and type(scalar) is type(entry[1]) and scalar == entry[1]:
            if len(entry) > 2:
                shifts[run[0]] = run[2] + place[len(run[0])][1] - run[1]
            else:
                run = (outer, index, shifts.get(outer, 0))
            position += 1
        elif not named:
            if entry is None:
                return f"BDS's JSON prints {scalar!r} past the case's last scalar"
            return f"{entry[0]} is {entry[1]!r} in the case and {scalar!r} in BDS's JSON"
    if position < len(printed):
        return f"{printed[position][0]} is {printed[position][1]!r} in the case and not in BDS's JSON"
    return None


class Server:
    """A bedrock_server under lldb, stopped where the script may call into it."""

    def __init__(self, lldb: Any, server: Path, build: Build) -> None:
        self.lldb = lldb
        self.build = build
        self.error = lldb.SBError()
        self.debugger = lldb.SBDebugger.Create()
        self.debugger.SetAsync(False)
        self.target = self.debugger.CreateTarget(str(server / "bedrock_server"))
        launch = lldb.SBLaunchInfo(None)
        launch.SetWorkingDirectory(str(server))
        launch.SetLaunchFlags(lldb.eLaunchFlagStopAtEntry)
        self.process = self.target.Launch(launch, self.error)
        if not self.error.Success():
            raise RuntimeError(f"bedrock_server: {self.error.GetCString()}")
        signals = self.process.GetUnixSignals()
        for name in ("SIGPIPE", "SIGUSR1", "SIGUSR2", "SIGALRM", "SIGCHLD", "SIGWINCH", "SIGPROF", "SIGURG", "SIGIO"):
            number = signals.GetSignalNumberFromName(name)
            signals.SetShouldStop(number, False)
            signals.SetShouldNotify(number, False)
        self.frame: Any = None
        self.options = lldb.SBExpressionOptions()
        self.options.SetIgnoreBreakpoints(True)
        self.options.SetUnwindOnError(True)
        self.options.SetTryAllThreads(False)
        self.options.SetTimeoutInMicroSeconds(60_000_000)
        self.options.SetLanguage(lldb.eLanguageTypeC_plus_plus)

    def address(self, file_address: int) -> int:
        return int(self.target.ResolveFileAddress(file_address).GetLoadAddress(self.target))

    def output(self) -> str:
        """Take what the server has printed to its terminal since the last call."""
        text = ""
        while chunk := self.process.GetSTDOUT(4096):
            text += chunk
        return text

    def stop_at(self, breakpoint: Any) -> Any:
        """Run to a breakpoint, delete it and return the frame it stopped in."""
        self.process.Continue()
        thread = self.process.GetSelectedThread()
        self.target.BreakpointDelete(breakpoint.GetID())
        if thread.GetStopReason() != self.lldb.eStopReasonBreakpoint:
            raise RuntimeError(f"bedrock_server: stopped in state {self.process.GetState()}, not at a breakpoint")
        return thread.GetFrameAtIndex(0)

    def call(self, function: int, *args: int) -> int:
        """Call a function in the server with integer or pointer arguments and return its result."""
        params = ", ".join("unsigned long" for _ in args)
        values = ", ".join(f"{arg}UL" for arg in args)
        value = self.frame.EvaluateExpression(f"((unsigned long (*)({params})){function})({values})", self.options)
        if not value.GetError().Success():
            raise RuntimeError(f"{function:#x}: {value.GetError().GetCString()}")
        return int(value.GetValueAsUnsigned())

    def alloc(self, data: bytes) -> int:
        address = int(
            self.process.AllocateMemory(
                max(1, len(data)), self.lldb.ePermissionsReadable | self.lldb.ePermissionsWritable, self.error
            )
        )
        if not self.error.Success():
            raise RuntimeError(f"alloc: {self.error.GetCString()}")
        if data:
            self.process.WriteMemory(address, data, self.error)
        return address

    def read(self, address: int, size: int) -> bytes:
        return bytes(self.process.ReadMemory(address, size, self.error)) if size else b""

    def u64(self, address: int) -> int:
        return int(struct.unpack("<Q", self.read(address, 8))[0])

    def string(self, address: int) -> bytes:
        """Read a libc++ std::string."""
        header = self.read(address, 24)
        if header[0] & 1:
            size, data = struct.unpack_from("<QQ", header, 8)
            return self.read(data, size)
        return header[1 : 1 + (header[0] >> 1)]

    def stream(self, data: bytes, vtable: int) -> tuple[int, int]:
        """Lay out a stream whose view is `data` and whose buffer is an empty std::string; return both."""
        buffer = self.alloc(bytes(24))
        view = self.alloc(data) if data else buffer + 1
        layout = bytearray(self.build.stream.size)
        layout[0:8] = struct.pack("<Q", self.address(vtable))
        layout[self.build.stream.view : self.build.stream.view + 16] = struct.pack("<QQ", view, len(data))
        layout[self.build.stream.buffer : self.build.stream.buffer + 8] = struct.pack("<Q", buffer)
        return self.alloc(bytes(layout)), buffer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path, help='JSON array of {"packet", "id", "value", "bytes", "printed"}')
    parser.add_argument("--server", type=Path, required=True, help="unpacked stock BDS; its ports are moved off 19132")
    parser.add_argument("--lldb", default="lldb", help="lldb executable whose Python module matches this python")
    args = parser.parse_args()
    server_dir = args.server.resolve()

    with (server_dir / "bedrock_server").open("rb") as binary:
        digest = hashlib.file_digest(binary, "sha256").hexdigest()
    if digest not in BUILDS:
        sys.exit(f"bedrock_server: no build in BUILDS has sha256 {digest}")
    build = BUILDS[digest]
    cases = json.loads(args.cases.read_text())
    lldb_executable = shutil.which(args.lldb)
    if lldb_executable is None:
        sys.exit(f"--lldb: no {args.lldb} on PATH")
    lldb_server = Path(lldb_executable).resolve().with_name("lldb-server")
    if not lldb_server.exists():
        sys.exit(f"--lldb: no lldb-server beside {Path(lldb_executable).resolve()}")
    os.environ["LLDB_DEBUGSERVER_PATH"] = str(lldb_server)
    lldb_path = subprocess.run([lldb_executable, "-P"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    sys.path.insert(0, lldb_path)
    lldb = importlib.import_module("lldb")

    for port in range(FIRST_PORT, 65535, 2):
        try:
            with (
                socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as v4,
                socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as v6,
            ):
                v4.bind(("0.0.0.0", port))
                v6.bind(("::", port + 1))
        except OSError:
            continue
        break
    settings = {"server-port": port, "server-portv6": port + 1, "enable-lan-visibility": "false"}
    properties = server_dir / "server.properties"
    kept = [line for line in properties.read_text().splitlines() if line.partition("=")[0].strip() not in settings]
    properties.write_text("\n".join([*kept, *(f"{key}={value}" for key, value in settings.items())]) + "\n")

    slots = build.slots
    reports = []
    log = server_dir / "bds.log"
    with log.open("w") as transcript:
        server = Server(lldb, server_dir, build)
        try:
            constructor = server.target.BreakpointCreateBySBAddress(
                server.target.ResolveFileAddress(build.server_network_system)
            )
            server_network_system = server.stop_at(constructor).FindRegister("rdi").GetValueAsUnsigned()
            listener = server.debugger.GetListener()
            event = lldb.SBEvent()
            server.debugger.SetAsync(True)
            server.process.Continue()
            printed = ""
            deadline = time.monotonic() + START_TIMEOUT
            while server.process.GetState() != lldb.eStateRunning or STARTED not in printed:
                if time.monotonic() > deadline:
                    raise RuntimeError(f"bedrock_server: no {STARTED!r} in {log}")
                if (
                    listener.WaitForEvent(1, event)
                    and event.GetType() & lldb.SBProcess.eBroadcastBitStateChanged
                    and lldb.SBProcess.GetStateFromEvent(event) != lldb.eStateRunning
                    and not lldb.SBProcess.GetRestartedFromEvent(event)
                ):
                    state = lldb.SBDebugger.StateAsCString(lldb.SBProcess.GetStateFromEvent(event))
                    raise RuntimeError(f"bedrock_server: {state} before {STARTED!r}, see {log}")
                text = server.output()
                transcript.write(text)
                transcript.flush()
                printed += text
            event.Clear()
            server.process.Stop()
            while not (
                event.GetType() & lldb.SBProcess.eBroadcastBitStateChanged
                and lldb.SBProcess.GetStateFromEvent(event) == lldb.eStateStopped
                and not lldb.SBProcess.GetRestartedFromEvent(event)
            ):
                if not listener.WaitForEvent(STOP_TIMEOUT, event):
                    raise RuntimeError(f"bedrock_server: not stopped {STOP_TIMEOUT}s after Stop")
            server.debugger.SetAsync(False)
            server.frame = server.stop_at(
                server.target.BreakpointCreateBySBAddress(server.target.ResolveFileAddress(build.run_events))
            )
            ctx = server.u64(server_network_system + build.reflection_ctx)
            if server.u64(ctx) != server.address(build.reflection_ctx_vtable):
                raise RuntimeError(f"reflection_ctx: {ctx:#x} is not a cereal::ReflectionCtx")

            for case in cases:
                seed = bytes.fromhex(case["bytes"])
                report: Json = {
                    "packet": case["packet"],
                    "id": case["id"],
                    "seed": case["bytes"],
                    "value": case["value"],
                }
                reports.append(report)
                try:
                    holder = server.alloc(bytes(64))
                    constructor = build.default_constructors.get(case["packet"])
                    if constructor is None:
                        server.call(server.address(build.create_packet), holder, case["packet"])
                    else:
                        server.call(server.address(constructor), holder, 0)
                    packet = server.u64(holder)
                    if not packet:
                        report["difference"] = "packet: createPacket builds nothing for this id"
                        continue
                    vtable = server.u64(packet)
                    virtuals = [server.u64(vtable + 8 * index) for index in range(slots.to_string + 1)]
                    mode = server.call(virtuals[slots.serialization_mode], packet) & 0xFFFFFFFF
                    report["writer"] = "manual" if mode < CEREAL_FIRST else "cereal"

                    stream, _ = server.stream(seed, build.read_only_binary_stream_vtable)
                    result = server.alloc(bytes(build.result_ok + 8))
                    server.call(virtuals[slots.read], result, packet, stream, ctx)
                    offset = server.u64(stream + build.stream.read_pointer)
                    report["read"] = {"offset": offset}
                    if not server.read(result + build.result_ok, 1)[0]:
                        code, category = struct.unpack("<i4xQ", server.read(result, 16))
                        name = server.call(server.u64(server.u64(category) + 16), category)
                        message = server.alloc(bytes(24))
                        server.call(server.u64(server.u64(category) + 48), message, category, code)
                        category_name = server.read(name, 64).split(b"\0")[0].decode()
                        report["read"]["error"] = f"{category_name}:{code}"
                        report["read"]["message"] = server.string(message).decode(errors="replace")
                        report["difference"] = f"read: {report['read']['error']} at byte {offset} of {len(seed)}"
                        continue

                    json_text = server.alloc(bytes(24))
                    server.call(virtuals[slots.to_string], json_text, packet)
                    shown_text = server.string(json_text).decode(errors="surrogateescape")
                    try:
                        report["bds_json"] = json.loads(shown_text) if shown_text else None
                    except ValueError:
                        report["bds_json"] = None
                        report["bds_text"] = shown_text

                    stream, buffer = server.stream(b"", build.binary_stream_vtable)
                    server.call(virtuals[slots.write], packet, stream, ctx)
                    report["bytes"] = server.string(buffer).hex()
                    if mode != CEREAL_ONLY:
                        other = (1 << 32) | (CEREAL_ONLY if report["writer"] == "manual" else MANUAL_ONLY)
                        stream, buffer = server.stream(b"", build.binary_stream_vtable)
                        server.call(virtuals[slots.write_with_mode], packet, stream, ctx, other)
                        report["other_writer_bytes"] = server.string(buffer).hex()

                    written = bytes.fromhex(report["bytes"])
                    if offset != len(seed):
                        report["difference"] = f"read: BDS stops at byte {offset} of {len(seed)}"
                    elif written != seed:
                        first = next(
                            i for i in range(max(len(written), len(seed))) if written[i : i + 1] != seed[i : i + 1]
                        )
                        report["difference"] = (
                            f"bytes: BDS writes {written.hex()}, first unlike the seed at byte {first}"
                        )
                    elif (gap := unmatched(tokens(shown_text), case["printed"])) is not None:
                        report["difference"] = f"json: {gap}"
                    else:
                        report["difference"] = None
                except (RuntimeError, ValueError) as error:
                    report["difference"] = f"bds: {error}"
        finally:
            transcript.write(server.output())
            server.process.Kill()
    json.dump({"build": build.version, "protocol": build.protocol, "cases": reports}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
