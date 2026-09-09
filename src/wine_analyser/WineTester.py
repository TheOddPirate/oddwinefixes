"""
Process Tester module for launching target executables within Wine and monitoring health.
"""

import os
import subprocess
import threading
from typing import Tuple, List, Dict, Any
from .WineLogAnalyzer import WineLogAnalyzer
from .DynamicWinetricksMapper import DynamicWinetricksMapper
from .WineEnvironment import WineEnvironment
from oddwinefixes.utils import get_logger

logger = get_logger(__name__)
class WineTester:
    """Handles execution, thread-safe log streaming, and font resolution fallbacks."""

    def __init__(
        self, wine_env: WineEnvironment, dynamic_mapper: DynamicWinetricksMapper
    ) -> None:
        self.wine_env = wine_env
        self.mapper = dynamic_mapper

    def test_run_exe(self, exe_path: str) -> Tuple[bool, bool, List[str], Dict[str, List[str]]]:
        """
        Executes the target application and monitors for log errors.
        
        Returns: 
            (user_confirmed_working, font_error_detected, missing_dlls_found, detected_gpu_issues)
        """
        exe_path = os.path.abspath(exe_path)
        exe_dir = os.path.dirname(exe_path)
        env = self.wine_env.get_exec_env()

        logger.info(f"[>] Launching {os.path.basename(exe_path)} with Wine...")

        log_lines: List[str] = []
        missing_dlls: List[str] = []
        font_error_detected = False
        steam_error_detcted = False
        gpu_issues: Dict[str, List[str]] = {
            "nvidia": [],
            "amd": [],
            "graphics_runtime": [],
        }

        def read_stream(stream):
            for line in iter(stream.readline, ""):
                log_lines.append(line)

                res = WineLogAnalyzer.analyze_line(line)
                if res:
                    nonlocal font_error_detected
                    res_type = res.get("type")

                    if res_type == "FONT_ERROR":
                        font_error_detected = True

                    elif res_type == "MISSING_DLL":
                        dll = res.get("file")
                        if dll and dll not in missing_dlls:
                            missing_dlls.append(dll)

                    elif res_type in ("NVIDIA_ISSUE", "AMD_ISSUE", "GRAPHICS_RUNTIME_ERROR"):
                        category = res_type.lower().replace("_issue", "")
                        match_text = res.get("match", line.strip())
                        if match_text not in gpu_issues.get(category, []):
                            gpu_issues[category].append(match_text)

            stream.close()

        try:
            process = subprocess.Popen(
                [self.wine_env.wine_bin, exe_path],
                env=env,
                cwd=exe_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            t1 = threading.Thread(target=read_stream, args=(process.stdout,))
            t2 = threading.Thread(target=read_stream, args=(process.stderr,))
            t1.daemon = True
            t2.daemon = True
            t1.start()
            t2.start()

        except Exception as e:
            logger.info(f"[-] Failed to launch process: {e}")
            return False, False, [], {"nvidia": [], "amd": [], "graphics_runtime": []}

        ans = input("\nDoes the program work as expected? (y/N): ").strip().lower()

        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

        if missing_dlls:
            logger.info(f"[!] Detected missing DLLs during execution: {', '.join(missing_dlls)}")
        has_gpu_errors = any(gpu_issues.values())
        if has_gpu_errors:
            for vendor, issues in gpu_issues.items():
                if issues:
                    logger.info(f"[!] Detected {vendor.upper()} / Graphics issues: {len(issues)} events captured.")

        return (ans in ["y", "yes"]), font_error_detected, missing_dlls, gpu_issues

    def handle_gpu_fallback(self, exe_path: str, gpu_issues: Dict[str, List[str]]) -> bool:
        """Kjører rettede Winetricks-verb og DLL-overrides basert på detekterte GPU/driver-feil."""
        logger.info("\n[!] GPU/Graphics runtime issue detected during log analysis.")
        
        gpu_verbs = []
        if gpu_issues.get("nvidia"):
            gpu_verbs.extend(["dxvk-nvapi", "physx"])
        if gpu_issues.get("amd"):
            gpu_verbs.extend(["vkd3d", "dxvk"])
        if gpu_issues.get("graphics_runtime") and not gpu_verbs:
            gpu_verbs.extend(["dxvk", "vkd3d"])

        if not gpu_verbs:
            return False

        logger.info(f"[->] Prioritizing GPU fixes based on log stream: {', '.join(gpu_verbs)}")

        for verb in gpu_verbs:
            logger.info(f"\n[->] Attempting GPU fix with verb: {verb}")
            self.mapper.install_verb(verb)


            is_working, _, _, _ = self.test_run_exe(exe_path)
            if is_working:
                logger.info(f"[+] Application successfully recovered after applying {verb}!")
                return True

        return False

    def handle_missing_dlls_fallback(self, exe_path: str, missing_dlls: List[str]) -> bool:
        """Installerer Winetricks-verb basert på direkte bekreftede DLL-mangler fra loggen."""
        logger.info(f"\n[!] Resolving {len(missing_dlls)} explicitly missing DLL(s) found in log stream...")

        resolved_verbs = self.mapper.resolve_dll(missing_dlls[0])

        if not resolved_verbs:
            logger.info("[-] Could not map detected missing DLLs to specific Winetricks verbs.")
            return False

        for verb in resolved_verbs:
            logger.info(f"\n[->] Attempting targeted DLL fix with verb: {verb}")
            self.mapper.install_verb(verb)

            is_working, _, _, _ = self.test_run_exe(exe_path)
            if is_working:
                logger.info(f"[+] Application successfully recovered after installing {verb}!")
                return True

        return False

    def handle_font_fallback(self, exe_path: str) -> bool:
        """Escalates to sequential font installs if a font issue is detected/confirmed."""
        logger.info("\n[!] Font issue suspected during execution.")
        ans = (
            input("[?] Do you want to try installing missing fonts? (y/N): ")
            .strip()
            .lower()
        )
        if ans not in ["y", "yes"]:
            return False

        font_verbs = ["corefonts", "tahoma", "segoeui", "allfonts"]

        for verb in font_verbs:
            logger.info(f"\n[->] Attempting font fix with Winetricks verb: {verb}")
            self.mapper.install_verb(verb)

            is_working, _, _, _ = self.test_run_exe(exe_path)
            if is_working:
                logger.info(
                    f"[+] Application successfully recovered after installing {verb}!"
                )
                return True

        logger.info("[-] All font installation attempts exhausted.")
        return False

    def run_and_check(self, exe_path: str) -> bool:
        """
        Intelligent triage wrapper around test_run_exe.
        Prioritizes exact runtime log findings before falling back to heavy PE heuristics.
        """
        is_working, font_error, missing_dlls, gpu_issues = self.test_run_exe(exe_path)

        if is_working:
            return True


        if missing_dlls:
            if self.handle_missing_dlls_fallback(exe_path, missing_dlls):
                return True


        if any(gpu_issues.values()):
            if self.handle_gpu_fallback(exe_path, gpu_issues):
                return True


        if font_error:
            if self.handle_font_fallback(exe_path):
                return True

        return False