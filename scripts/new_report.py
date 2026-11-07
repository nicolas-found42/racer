"""Create-new output for the bounded report generators (car_stages and the Juiced 2 wheel tools)."""
from pathlib import Path


def write_new_report(path, payload, max_bytes):
    """Write `payload` to a new file. Over budget, an existing path and a missing parent directory are
    one-line SystemExits naming the path; nothing is created on failure and reports are never overwritten."""
    path = Path(path)
    if len(payload) > max_bytes:
        raise SystemExit(f'output budget exceeded: {len(payload)} > {max_bytes}')
    if not path.parent.is_dir():
        raise SystemExit(f'output directory does not exist: {path.parent}')
    try:
        stream = path.open('xb')
    except FileExistsError:
        raise SystemExit(f'{path} already exists; reports are never overwritten, choose a new name')
    except OSError as error:
        raise SystemExit(f'cannot create {path}: {error.strerror}')
    with stream:
        stream.write(payload)
