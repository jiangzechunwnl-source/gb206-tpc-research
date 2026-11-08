#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# RM allocation/query sequence adapted from JustAResearcher/gpu-unlock-ada,
# tools/read_sm_rates.py (GPL-2.0-only), via native-linux-readonly/read_gb206_rates.py.
"""Print a fixed GB206 read-only comparison batch as JSON on native Linux."""

import csv
import ctypes as C
import fcntl
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys

U32, U64 = C.c_uint32, C.c_uint64
DRIVER = "595.99.02"
OFFSETS = (0x820C38, 0x820C3C, 0x820C40, 0x820838, 0x82083C, 0x820840)
SENTINEL = 0xDEADBEEF


class Alloc(C.Structure):
    _fields_ = [(name, U32) for name in ("root", "parent", "new", "cls")] + [
        ("params", U64), ("rights", U64), ("size", U32), ("flags", U32), ("status", U32)
    ]


class Control(C.Structure):
    _fields_ = [(name, U32) for name in ("client", "obj", "cmd", "flags")] + [
        ("params", U64), ("size", U32), ("status", U32)
    ]


class Device(C.Structure):
    _fields_ = [(name, U32) for name in ("device", "share", "target_client", "target_device", "flags")] + [
        ("va_size", U64), ("va_start", U64), ("va_limit", U64), ("va_mode", U32)
    ]


class Op(C.Structure):
    _fields_ = [(name, C.c_uint8) for name in ("op", "type", "status", "quad")] + [
        (name, U32) for name in ("group", "subgroup", "offset", "hi", "lo", "maskhi", "masklo")
    ]


class Route(C.Structure):
    _fields_ = [("flags", U32), ("route", U64)]


class Params(C.Structure):
    _fields_ = [(name, U32) for name in (
        "client_target", "channel_target", "nontransactional", "reserved0", "reserved1", "count"
    )] + [("ops", U64), ("route", Route)]


def identify():
    kernel = platform.release()
    if platform.system() != "Linux" or "microsoft" in kernel.lower() or Path("/dev/dxg").exists():
        raise RuntimeError("Use native Linux with the NVIDIA driver already loaded.")
    output = subprocess.run(
        ["nvidia-smi", "--query-gpu=pci.bus_id,pci.device_id,name,driver_version",
         "--format=csv,noheader,nounits"],
        check=True, capture_output=True, text=True, timeout=10,
    )
    rows = list(csv.reader(output.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) != 4:
        raise RuntimeError("Expected one NVIDIA GPU; multiple GPU instances are unsupported.")
    bus, pci_id, name, driver = (item.strip() for item in rows[0])
    device = {0x2D5910DE: "2d59", 0x2D0410DE: "2d04"}.get(int(pci_id, 16))
    if device is None or driver != DRIVER:
        raise RuntimeError(f"Requires PCI 10de:2d59 or 10de:2d04 and NVIDIA {DRIVER}.")
    domain, pci_bus, function = bus.lower().split(":")
    bdf = f"{int(domain, 16):04x}:{pci_bus}:{function}"
    pci = Path("/sys/bus/pci/devices") / bdf
    if ((pci / "vendor").read_text().strip(), (pci / "device").read_text().strip()) != ("0x10de", "0x" + device):
        raise RuntimeError("sysfs and nvidia-smi disagree on GPU identity.")
    if (pci / "driver").resolve(strict=True).name != "nvidia":
        raise RuntimeError("The native NVIDIA driver must already be bound.")
    info = Path("/proc/driver/nvidia/gpus") / bdf / "information"
    if not any(line.split() == ["Device", "Minor:", "0"] for line in info.read_text().splitlines()):
        raise RuntimeError("The selected GPU does not identify itself as /dev/nvidia0.")
    return dict(name=name, pci_device_id=f"10de:{device}", driver=driver, kernel=kernel)


def ioctl(fd, operation, request):
    buffer = bytearray(bytes(request))
    number = (3 << 30) | (len(buffer) << 16) | (ord("F") << 8) | operation
    fcntl.ioctl(fd, number, buffer, True)
    C.memmove(C.addressof(request), bytes(buffer), len(buffer))
    return request.status


def collect():
    expected = {Alloc: 48, Control: 32, Device: 56, Op: 32, Params: 48}
    if (C.sizeof(C.c_void_p) != 8 or any(C.sizeof(cls) != size for cls, size in expected.items())
            or Op.offset.offset != 12 or Params.route.offset != 32):
        raise RuntimeError("The local ABI does not match the audited structures.")
    gpu = identify()
    fds = []
    try:
        for path in ("/dev/nvidiactl", "/dev/nvidia0"):
            fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
            fds.append(fd)
            if not stat.S_ISCHR(os.fstat(fd).st_mode):
                raise RuntimeError(f"{path} is not a character device.")

        def allocate(root, parent, cls, params=None):
            request = Alloc(root=root, parent=parent, cls=cls,
                            params=C.addressof(params) if params is not None else 0,
                            size=C.sizeof(params) if params is not None else 0)
            status = ioctl(fds[0], 0x2B, request)
            if status or not request.new:
                raise RuntimeError(f"Temporary RM allocation failed: {status:#x}")
            return request.new

        client = allocate(0, 0, 0x41)
        device = allocate(client, client, 0x80, Device())
        subdevice = allocate(client, device, 0x2080, U32(0))
        # REG_OP_READ_32 and REG_OP_TYPE_GLOBAL are both zero. Write masks stay zero.
        ops = (Op * len(OFFSETS))(*(Op(offset=offset, lo=SENTINEL, hi=SENTINEL) for offset in OFFSETS))
        params = Params(nontransactional=1, count=len(ops), ops=C.addressof(ops))
        request = Control(client=client, obj=subdevice, cmd=0x20800122,
                          params=C.addressof(params), size=C.sizeof(params))
        status = ioctl(fds[0], 0x2A, request)
    finally:
        for fd in reversed(fds):
            os.close(fd)

    rows = []
    for offset, op in zip(OFFSETS, ops):
        row = dict(offset=hex(offset), status=hex(op.status))
        if status == 0 and op.status == 0 and op.lo != SENTINEL:
            row["raw_value"] = hex(op.lo)
        rows.append(row)
    return dict(gpu=gpu, administrator=os.geteuid() == 0, request_status=hex(status),
                register_writes=False, rows=rows)


if __name__ == "__main__":
    try:
        print(json.dumps(collect(), indent=2))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
