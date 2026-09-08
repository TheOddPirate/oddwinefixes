import os
from oddwinefixes.const import DEBUG
from oddwinefixes.utils import get_logger

logger = get_logger(__name__)

class WineEnvironment:
    """Universal environment manager for all types of Wine and Proton prefixes."""

    def __init__(self, prefix_path):
        self.prefix_path = os.path.abspath(prefix_path)
        self.wine_bin = "wine"
        self.wineserver_bin = "wineserver"
        self.winetricks_bin = "winetricks"
        self.winecfg_bin = "winecfg"
        self.env_vars = {}
        self.proton_version = "Unknown"
        self.proton_root = "Unknown"
        self._detect_environment()

    def _detect_environment(self):
        """Detects runner configuration without locking into specific wrappers."""
        config_file = os.path.join(self.prefix_path, "config_info")
        if not os.path.exists(config_file):
            return

        try:
            with open(config_file, "r") as f:
                lines = [line.strip() for line in f.readlines()]
            self.proton_version = lines[0]
            for line in lines[1:3]:
                if "/files/" in line:
                    proton_root = line.split("/files/")[0]
                    if os.path.exists(proton_root):
                        self.proton_root = proton_root
                    files_dir = os.path.join(proton_root, "files")

                    candidate_wine = os.path.join(files_dir, "bin", "wine")
                    
                    candidate_wineserver = os.path.join(files_dir, "bin", "wineserver")

                    candidate_winecfg = os.path.join(
                        files_dir, "lib", "wine", "i386-windows", "winecfg.exe"
                    )
                    candidate_winetricks = os.path.join(
                        proton_root, "protonfixes", "winetricks"
                    )

                    if os.path.exists(candidate_wine):
                        self.wine_bin = candidate_wine
                        if DEBUG:
                            logger.info(f"setting wine to:{self.wine_bin}")
                    if os.path.exists(candidate_wineserver):
                        self.wineserver_bin = candidate_wineserver
                        if DEBUG:
                            logger.info(f"setting wineserver to:{self.wineserver_bin}")
                    if os.path.exists(candidate_winecfg):
                        self.winecfg_bin = candidate_winecfg
                        if DEBUG:
                            logger.info(f"setting winecfg to:{self.winecfg_bin}")
                    if os.path.exists(candidate_winetricks):
                        self.winetricks_bin = candidate_winetricks
                        if DEBUG:
                            logger.info(f"setting winetricks to:{self.winetricks_bin}")
                    elif os.path.exists(os.path.join(files_dir, "bin", "winetricks")):
                        self.winetricks_bin = os.path.join(files_dir, "bin", "winetricks")
                        if DEBUG:
                            logger.info(f"setting winetricks to:{self.winetricks_bin}")
                    bin_dir = os.path.join(files_dir, "bin")
                    if os.path.exists(bin_dir):
                        self.env_vars["PATH"] = (f"{bin_dir}:{os.environ.get('PATH', '')}")
                    break

        except Exception as e:
            print(f"[!] Warning reading config_info: {e}. Falling back to system wine.")

    def get_exec_env(self):
        """Builds a complete, safe execution environment preserving Display/X11/Wayland context."""
        env = os.environ.copy()
        env["WINEPREFIX"] = self.prefix_path
        env["WINEDEBUG"] = "-all"

        if self.env_vars:
            env.update(self.env_vars)

        return env
