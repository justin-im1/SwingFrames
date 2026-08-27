from __future__ import annotations

import asyncio
import shutil
from functools import lru_cache
from pathlib import Path


class FfmpegError(RuntimeError):
    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


@lru_cache(maxsize=4)
def find_binary(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for folder in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = folder / name
        if candidate.exists():
            return str(candidate)
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:  # noqa: BLE001
            raise FfmpegError(
                "ffmpeg not found. Install it (brew install ffmpeg) or pip install imageio-ffmpeg."
            ) from exc
    raise FfmpegError(
        f"{name} not found on PATH. Install ffmpeg (brew install ffmpeg)."
    )


async def run_exec(
    *args: str,
    timeout: float = 180.0,
    input_bytes: bytes | None = None,
    allow_nonzero: bool = False,
) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input_bytes), timeout=timeout
        )
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise FfmpegError(f"Timed out: {' '.join(args[:4])}") from exc
    code = proc.returncode or 0
    if code != 0 and not allow_nonzero:
        err = stderr.decode("utf-8", errors="replace")[-4000:]
        raise FfmpegError(
            f"{args[0]} failed ({code}): {err[-800:]}", stderr=err
        )
    return code, stdout, stderr


async def ffmpeg(*args: str, timeout: float = 180.0) -> tuple[bytes, bytes]:
    _, stdout, stderr = await run_exec(find_binary("ffmpeg"), *args, timeout=timeout)
    return stdout, stderr


async def ffprobe(*args: str, timeout: float = 120.0) -> tuple[bytes, bytes]:
    try:
        _, stdout, stderr = await run_exec(find_binary("ffprobe"), *args, timeout=timeout)
        return stdout, stderr
    except FfmpegError:
        raise


def has_ffprobe() -> bool:
    try:
        find_binary("ffprobe")
        return True
    except FfmpegError:
        return False


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
