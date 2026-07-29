import subprocess
import os
import sys
from pathlib import Path

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    from PySide6.QtCore import QThread, Signal as pyqtSignal

class ProcessRunnerThread(QThread):
    output_line = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    finished_signal = pyqtSignal(int, str)

    def __init__(self, command: list, cwd: str = None, parent=None):
        super().__init__(parent)
        self.command = command
        self.cwd = cwd or str(Path(__file__).parents[3])
        self.process = None
        self._is_cancelled = False

    def run(self):
        env = os.environ.copy()
        # Force unbuffered output
        env["PYTHONUNBUFFERED"] = "1"
        env["PAGER"] = "cat"

        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
                env=env,
                bufsize=1
            )

            full_output = []
            for line in iter(self.process.stdout.readline, ''):
                if self._is_cancelled:
                    self.process.terminate()
                    break
                line_str = line.rstrip()
                full_output.append(line_str)
                self.output_line.emit(line_str)

                # Try parsing percentage progress if line contains %
                if "%" in line_str:
                    import re
                    match = re.search(r'(\d+)%', line_str)
                    if match:
                        try:
                            val = int(match.group(1))
                            if 0 <= val <= 100:
                                self.progress_changed.emit(val)
                        except ValueError:
                            pass

            self.process.wait()
            return_code = self.process.returncode if not self._is_cancelled else -1
            self.finished_signal.emit(return_code, "\n".join(full_output))
        except Exception as e:
            self.output_line.emit(f"[ERR] Failed to execute process: {str(e)}")
            self.finished_signal.emit(-1, str(e))

    def cancel(self):
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            self.process.terminate()
