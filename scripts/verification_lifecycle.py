"""Best-effort bounded verifier status; never stores commands or exception text."""
import json
import os
from pathlib import Path
import subprocess
import time

PHASES = frozenset(('preflight', 'spawn', 'process', 'capture', 'retrieval', 'validation', 'complete'))
MAX_PROCESSES = 64
MAX_BYTES = 32768

class VerificationLifecycle:
    """One fresh output directory; caller retains process cleanup and result policy.

    The sidecar is replaced atomically, but is not a power-loss durable backup.
    Write failure cannot replace the original verifier result or exception.
    """
    def __init__(self, output):
        self.output = Path(output)
        self.started = time.monotonic()
        self.active = []
        self.current_process = None
        self.record = {'schema': 1, 'status': 'running', 'phase': 'preflight',
                       'started_unix_ms': int(time.time()*1000), 'elapsed_ms': 0,
                       'processes': [], 'omitted_processes': 0,
                       'diagnostic_write_failures': 0, 'error_code': None, 'errno': None}

    def __enter__(self):
        self._write()
        return self

    def _write(self):
        temporary = self.output / '.lifecycle.tmp'
        owned = False
        try:
            self.record['elapsed_ms'] = max(0, int((time.monotonic()-self.started)*1000))
            data = (json.dumps(self.record, separators=(',', ':'), allow_nan=False)+'\n').encode()
            if len(data) > MAX_BYTES:
                raise ValueError('bounded diagnostic payload exceeded')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            owned = True
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            os.replace(temporary, self.output / 'lifecycle.json')
        except Exception:
            self.record['diagnostic_write_failures'] += 1
        finally:
            if owned:
                try: temporary.unlink(missing_ok=True)
                except OSError: pass

    def phase(self, phase):
        if phase not in PHASES: raise ValueError('unknown verification phase')
        if self.record['phase'] == phase: return
        self.record['phase'] = phase
        self._write()

    def checkpoint(self):
        """Persist changed bounded context even when the phase is unchanged."""
        self._write()

    def _process(self, kind):
        if kind not in ('native', 'reload', 'retrieval'): raise ValueError('unknown process kind')
        self.phase('retrieval' if kind == 'retrieval' else 'spawn')
        row = {'kind': kind, 'status': 'starting', 'exit': None, 'timeout': False}
        self.current_process = row
        if len(self.record['processes']) < MAX_PROCESSES:
            self.record['processes'].append(row)
        else:
            self.record['omitted_processes'] += 1
        self._write()
        return row

    def run(self, *args, kind='native', **kwargs):
        row = self._process(kind)
        self.phase('retrieval' if kind == 'retrieval' else 'process')
        try:
            result = subprocess.run(*args, **kwargs)
        except subprocess.TimeoutExpired:
            row.update(status='timeout', timeout=True)
            self._write()
            raise
        except OSError:
            row['status'] = 'spawn_failed'
            self.phase('spawn')
            raise
        row.update(status='returned', exit=result.returncode)
        self._write()
        return result

    def popen(self, *args, kind='native', **kwargs):
        row = self._process(kind)
        try:
            process = subprocess.Popen(*args, **kwargs)
        except OSError:
            row['status'] = 'spawn_failed'
            self._write()
            raise
        pid = getattr(process, 'pid', None)
        row.update(status='running', pid=pid if type(pid) is int else None)
        if len(self.active) < MAX_PROCESSES:
            self.active.append((process, row))
        self.phase('process')
        return process

    def process_done(self, process, *, timed_out=False):
        for active, row in self.active:
            if active is process:
                row.update(status='timeout' if timed_out else 'returned', exit=process.returncode, timeout=timed_out)
        self._write()

    def complete(self, success=True):
        self.record.update(status='completed' if success else 'failed',
                           error_code=None if success else 'verification_failed')
        self.phase('complete' if success else 'validation')

    def __exit__(self, kind, error, traceback):
        # Even diagnostic field construction/polling must not hide the original
        # exception. Process termination remains the existing caller's job.
        try:
            for process, row in self.active:
                unfinished = row['status'] == 'running' and row is self.current_process
                result = process.poll()
                if result is not None and row['status'] == 'running':
                    row.update(status='returned', exit=result)
                if unfinished and isinstance(error, (TimeoutError, subprocess.TimeoutExpired)):
                    row.update(status='timeout', timeout=True)
            if error is not None:
                code = ('timeout' if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else
                        'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else
                        'assertion_failed' if isinstance(error, AssertionError) else
                        'spawn_failed' if isinstance(error, OSError) and self.record['phase'] == 'spawn' else
                        'io_error' if isinstance(error, OSError) else
                        'invalid_data' if isinstance(error, (ValueError, TypeError)) else 'unexpected_error')
                self.record.update(status='failed', error_code=code,
                                   errno=error.errno if isinstance(error, OSError) and type(error.errno) is int else None)
            elif self.record['status'] == 'running':
                self.complete()
            self.record['finished_unix_ms'] = int(time.time()*1000)
            self._write()
        except Exception:
            pass
        return False
