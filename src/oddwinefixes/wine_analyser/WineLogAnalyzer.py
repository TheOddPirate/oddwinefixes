"""
Log Analyzer module for parsing Wine/Proton stderr/stdout streams.
"""

from typing import Dict, Optional, Any
from oddwinefixes.const import LOG_PATTERNS


class WineLogAnalyzer:
    """Parses streaming log lines from Wine processes to identify runtime failures."""

    @staticmethod
    def analyze_line(line: str) -> Optional[Dict[str, Any]]:
        """Analyzes a single log line fortløpende as it streams from Wine."""
        dll_match = LOG_PATTERNS["missing_dll"].search(line)
        if dll_match:
            return {
                "type": "MISSING_DLL",
                "file": dll_match.group(1).lower(),
                "raw_log": line.strip(),
            }

        if LOG_PATTERNS["font_issue"].search(line):
            return {"type": "FONT_ERROR", "raw_log": line.strip()}
        
        if LOG_PATTERNS["entrypoint_missing"].search(line):
            return {"type": "ENTRYPOINT_ERROR", "raw_log": line.strip()}


        if LOG_PATTERNS["graphics_runtime_error"].search(line):
            return {"type": "GRAPHICS_RUNTIME_ERROR", "raw_log": line.strip()}

        if LOG_PATTERNS["amd_issue"].search(line):
            return {"type": "AMD_ISSUE", "raw_log": line.strip()}
        if LOG_PATTERNS["nvidia_issue"].search(line):
            return {"type": "NVIDIA_ISSUE", "raw_log": line.strip()}



        return None
