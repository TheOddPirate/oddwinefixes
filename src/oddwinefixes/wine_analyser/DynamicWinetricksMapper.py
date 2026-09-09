import subprocess
import re

from oddwinefixes.const import WINDOWS_VERSION_MAP, DOTNET_RELEASE_MAP
from .WineEnvironment import WineEnvironment
from oddwinefixes.utils.logger import get_logger, setup_logging
from oddwinefixes.const import DEBUG

logger = get_logger(__name__)

class DynamicWinetricksMapper:
    """Dynamic lookup against Winetricks to eliminate static app databases."""

    def __init__(self, wine_env: WineEnvironment):
        self.wine_env = wine_env
        self.available_verbs = self._scan_winetricks_verbs()
        self.installed_verbs = self._scan_installed_verbs()
        self.windows_version = self._get_windows_version()

    def _scan_winetricks_verbs(self):
        """Fetches all available verbs from the active Winetricks instance."""
        env = self.wine_env.get_exec_env()
        verbs = set()
        if DEBUG:
            logger.debug(f"Scanning prefix {self.wine_env.prefix_path} for available Winetricks verbs")

        for category in ["dlls", "apps"]:
            try:
                res = subprocess.run(
                    [self.wine_env.winetricks_bin, category, "list"],
                    capture_output=True,
                    text=True,
                    env=env,
                    check=True,
                )
                for line in res.stdout.splitlines():
                    parts = line.strip().split()
                    if parts and not line.startswith("Executing"):
                        verbs.add(parts[0])
            except Exception as e:
                print(f"[-] Error scanning Winetricks {category}: {e}")

        return verbs

    def _scan_installed_verbs(self):
        """Checks what packages are currently installed in the target prefix."""
        if DEBUG:
            logger.debug(f"Scanning prefix {self.wine_env.prefix_path} for installed winetricks verbs")

        env = self.wine_env.get_exec_env()
        try:
            res = subprocess.run(
                [self.wine_env.winetricks_bin, "list-installed"],
                capture_output=True,
                text=True,
                env=env,
            )
            installed = [
                line.strip()
                for line in res.stdout.splitlines()
                if not line.startswith("Executing") and "remove_mono" not in line
            ]

            return set(installed)
        except Exception as e:
            print(f"[-] detecting installed verbs: {e}")
            return set()

    def _get_windows_version(self):
        env = self.wine_env.get_exec_env()

        try:
            res = subprocess.run(
                [self.wine_env.wine_bin, self.wine_env.winecfg_bin, "/v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            for line in res.stdout.splitlines():
                clean_line = line.strip().lower()
                if clean_line in WINDOWS_VERSION_MAP:
                    return WINDOWS_VERSION_MAP[clean_line]

            return "Unknown"

        except Exception as e:
            print(f"Feil i _get_windows_version: {e}")
            return "Unknown"

    def set_windows_version(self, version: str = "win11"):
        if not version in WINDOWS_VERSION_MAP:
            print(f"[-] Can not set windows version to: {version}")
            print(f"[!] Supported options are: {', '.join(WINDOWS_VERSION_MAP.keys())}")
            return False

        env = self.wine_env.get_exec_env()

        try:
            print(
                f"[+] Changing prefix win version from {self.windows_version} to {WINDOWS_VERSION_MAP[version]}"
            )
            res = subprocess.run(
                [self.wine_env.wine_bin, self.wine_env.winecfg_bin, "/v", version],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            self.windows_version = self._get_windows_version() 
            return True

        except Exception as e:
            print(f"[-] Failed to change windows version: {e}")
            return False

    def resolve_dll(self, dll_name):
        """Matches a detected DLL to available packages in Winetricks."""
        dll_clean = dll_name.lower().replace(".dll", "")
        matches = []
        # .NET Framework / Desktop Runtimes
        if dll_clean in ["mscoree", "clr", "mscorwks"]:
            desktop_verbs = sorted(
                [v for v in self.available_verbs if v.startswith("dotnetdesktop")],
                reverse=True,
            )
            framework_verbs = sorted(
                [v for v in self.available_verbs if re.match(r"^dotnet\d+$", v)],
                reverse=True,
            )
            matches.extend(desktop_verbs + framework_verbs)

        # Visual C++ Redistributables
        elif "msvcp" in dll_clean or "msvcr" in dll_clean or "vcruntime" in dll_clean:
            vcruntime = sorted(
                [v for v in self.available_verbs if v.startswith("vcrun")], reverse=True
            )
            matches.extend(vcruntime)

        # DirectX / Direct3D
        elif dll_clean.startswith("d3dx9"):
            if "d3dx9" in self.available_verbs:
                matches.append("d3dx9")
        elif dll_name == "mfplat.dll":
            if "mf" in self.available_verbs:
                matches.append("mf")
        elif dll_clean in self.available_verbs:
            matches.append(dll_clean)

        return matches

    def install_verb(self, verb: str, force_retry: bool = False):
        """Installs the selected Winetricks package silently with a clean retry."""
        command = [self.wine_env.winetricks_bin, "-q"]
        if force_retry:
            command.append("--force")
        command.append(verb)

        logger.info(f"[+] Installing {verb} (force={force_retry})...")

        result = subprocess.run(command, env=self.wine_env.get_exec_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True )

        installed = self._scan_installed_verbs()

        if verb in installed:
            logger.debug(f"[+] Successfully installed {verb}")
            self.installed_verbs = installed
            return True

        logger.warning(f"[-] Failed to install {verb}.")
        if result.stderr:
            logger.debug(f"[winetricks stderr]: {result.stderr.strip()}")

        if not force_retry:
            logger.info(f"[!] Cleaning up wineserver and retrying {verb} with --force...")
            
            return self.install_verb(verb, force_retry=True)
        else:
            logger.error(f"[-] Critical: Failed to install {verb} even with --force.")
            return False

    def prioritize_verbs_by_year(self, verbs: list[str], build_year: int | None) -> list[str]:
        """Sorts verbs (e.g. vcrun or dotnet) according to proximity to target build year."""
        if not build_year:
            return verbs

        def calculate_score(verb: str) -> int:
            verb_lower = verb.lower()

            match = re.search(r"\d{4}", verb)
            if match:
                target = int(match.group())
                return abs(build_year - target)

            for dotnet_verb, year in DOTNET_RELEASE_MAP.items():
                if dotnet_verb in verb_lower:
                    return abs(build_year - year)

            return 999  

        return sorted(verbs, key=calculate_score)



    def create_fresh_prefix(self, target_path: str) -> WineEnvironment:
        """
        TODO fix this mess, not working yet
        """
        target_path = os.path.abspath(target_path)
        
        if os.path.exists(target_path):
            logger.info(f"[!] Target temp prefix already exists. Cleaning up: {target_path}")
            shutil.rmtree(target_path, ignore_errors=True)

        logger.info(f"[+] Initializing fresh, isolated WINEPREFIX at: {target_path}")
        os.makedirs(target_path, exist_ok=True)

        fresh_env = self.get_exec_env()
        fresh_env["WINEPREFIX"] = target_path

        try:
            subprocess.run(
                [self.wine_bin, "wineboot", "-u"],
                env=fresh_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            logger.info("[+] Fresh WINEPREFIX successfully initialized.")
        except Exception as e:
            logger.error(f"[-] Failed to initialize fresh prefix via wineboot: {e}")

        new_wine_env = WineEnvironment(target_path)
        new_wine_env.wine_bin = self.wine_bin
        new_wine_env.wineserver_bin = self.wineserver_bin
        new_wine_env.winetricks_bin = self.winetricks_bin
        new_wine_env.winecfg_bin = self.winecfg_bin
        new_wine_env.proton_version = self.proton_version
        new_wine_env.proton_root = self.proton_root
        new_wine_env.env_vars = self.env_vars.copy()

        return new_wine_env