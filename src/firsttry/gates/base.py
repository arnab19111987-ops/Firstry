"""Compatibility base classes and types for FirstTry gates."""
from __future__ import annotations

from typing import List, Sequence, Optional, Any


class GateResult:
    """Flexible GateResult that supports both old and new parameter styles."""
    
    def __init__(self, *args, **kwargs):
        # Default values
        self.gate_id = ""
        self.ok = True
        self.output = ""
        self.skipped = False
        self.reason = ""
        self.watched_files = []
        
        # Handle positional arguments (old style): name, status, info, details, returncode, out, err
        if args:
            if len(args) >= 1:
                self.gate_id = args[0]  # name
            if len(args) >= 2:
                status = args[1]  # status
                if status == "SKIPPED":
                    self.ok = True  # Skipped is considered "ok" but skipped
                    self.skipped = True
                else:
                    self.ok = status == "PASS"
            if len(args) >= 3:
                self.reason = args[2]  # info
            if len(args) >= 4:
                self.output = args[3]  # details
            if len(args) >= 5:
                self.ok = args[4] == 0  # returncode
            # args[5] and args[6] would be stdout/stderr but we'll ignore them for now
        
        # Handle keyword arguments (new style and overrides)
        if 'gate_id' in kwargs:
            self.gate_id = kwargs['gate_id']
        if 'name' in kwargs:
            self.gate_id = kwargs['name']
        if 'ok' in kwargs:
            self.ok = kwargs['ok']
        if 'status' in kwargs:
            self.ok = kwargs['status'] == "PASS"
        if 'output' in kwargs:
            self.output = kwargs['output']
        if 'details' in kwargs:
            self.output = kwargs['details']
        if 'skipped' in kwargs:
            self.skipped = kwargs['skipped']
        if 'reason' in kwargs:
            self.reason = kwargs['reason']
        if 'info' in kwargs:
            self.reason = kwargs['info']
        if 'watched_files' in kwargs:
            self.watched_files = kwargs['watched_files'] or []
        if 'returncode' in kwargs:
            self.ok = kwargs['returncode'] == 0
            
        # Set any additional kwargs as attributes
        for k, v in kwargs.items():
            if k not in ['gate_id', 'name', 'ok', 'status', 'output', 'details', 
                        'skipped', 'reason', 'info', 'watched_files', 'returncode']:
                setattr(self, k, v)
    
    @property
    def name(self):
        """Return gate_id as name for compatibility."""
        return self.gate_id
    
    @property
    def status(self):
        """Return status string for compatibility."""
        if self.skipped:
            return "SKIPPED"
        elif self.ok:
            return "PASS"
        else:
            return "FAIL"
    
    @property
    def info(self):
        """Return reason for compatibility."""
        return self.reason
    
    @property
    def details(self):
        """Return output for compatibility."""
        return self.output
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'gate_id': self.gate_id,
            'ok': self.ok,
            'output': self.output,
            'stdout': self.output,  # Provide stdout as alias for output
            'stderr': '',  # Most gates don't separate stderr, default to empty
            'status': self.status,  # Include status field
            'skipped': self.skipped,
            'reason': self.reason,
            'watched_files': self.watched_files,
            'returncode': 0 if self.ok else 1
        }
    
    def __json__(self):
        """Support for JSON serialization."""
        return self.to_dict()


class Gate:
    gate_id: str = "base"
    # which patterns this gate is interested in
    patterns: Sequence[str] = ("*.py",)
    
    def run(self, project_root: Optional[Any] = None) -> GateResult:
        """Override in subclasses."""
        return GateResult(gate_id=self.gate_id, ok=True, output="")
    
    def should_run_for(self, files: List[str]) -> bool:
        """Check if gate should run for given files (compatibility)."""
        if not files:
            return False
        # Check if any file matches our patterns
        import fnmatch
        for file in files:
            for pattern in self.patterns:
                if fnmatch.fnmatch(file, pattern):
                    return True
        return False