import os
import re
import math
import pefile
import peutils

from datetime import datetime, timezone
from pathlib import Path

from oddwinefixes.const import (
    KNOWN_OS_LIBS, 
    KNOWN_GAME_BUNDLED_LIBS, 
    KNOWN_GRAPHICS_LIBS, 
    KNOWN_MEDIA_FRAMEWORKS
)
from oddwinefixes.utils.logger import get_logger

logger = get_logger(__name__)

class PEanalyser:
    """Analyzes Windows PE executables to extract framework, architecture, and dependency requirements."""

    def __init__(self, exe_path: str, printlogs: bool = False):
        if not exe_path or not os.path.exists(exe_path):
            raise FileNotFoundError(f"Executable path {exe_path} invalid or does not exist")

        logger.info(f"[+] Loading PEanalyser for: {exe_path}")
        self.exe_path = exe_path
        
        self.pe = pefile.PE(exe_path, fast_load=True)
        self.pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR'],
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE'],
        ])

        self.all_imports = self._get_all_imports()
        
        (
            self.os_dlls, 
            self.game_bundled_dlls, 
            raw_custom, 
            self.graphics_api, 
            self.media_frameworks
        ) = self._categorize_imports()
        
        self.custom_dlls, self.disk_found_custom_dlls = self.sanitize_custom_imports(raw_custom)

        self.missing_game_files = self.verify_game_files_on_disk()

        self.arch = self._get_architecture()
        self.is_packed_or_encrypted = self._check_is_packed_or_encrypted()
        self.is_dotnet = self._check_is_dotnet()
        self.min_win_ver = self._get_min_windows_version()
        self.version_info = self._get_version_info()
        self.build_year = self._determine_build_year()
        #disabled because hardcoded personal path atm
       # self.detect_packer_name()
        
        if printlogs:
            self._print_debug_info()

    def _print_debug_info(self):
        """Prints debug information about the binary."""
        logger.info(f"All imports (total): {len(self.all_imports)} items")
        logger.info(f"OS/Wine DLLs (ignored): {len(self.os_dlls)} items")
        logger.info(f"Game Bundled DLLs: {self.game_bundled_dlls}")
        logger.info(f"Custom/External DLLs (Needs mapping): {self.custom_dlls}")
        logger.info(f"Custom DLLs found on disk (Reclassified): {self.disk_found_custom_dlls}")
        logger.info(f"Graphics API: {self.graphics_api}")
        logger.info(f"Media frameworks: {self.media_frameworks}")
        logger.info(f"Architecture: {self.arch}")
        logger.info(f"Is packed or encrypted? {self.is_packed_or_encrypted}")
        logger.info(f"Is .NET? {self.is_dotnet}")
        logger.info(f"Min Windows version: {self.min_win_ver}")
        logger.info(f"Version info metadata: {self.version_info}")
        logger.info(f"Determined build year: {self.build_year}") 

    def _categorize_imports(self) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
        """
        Categorizes imported DLLs into OS/Wine libraries, graphics APIs, media frameworks, 
        known bundled game DLLs, and raw unclassified custom dependencies.
        """
        os_dlls = set()
        game_bundled = set()
        gfx_libs = set()
        media_libs = set()
        custom = set()

        detected_media = self._detect_media_deps()

        for dll in self.all_imports:
            dll_lower = dll.lower().strip()

            # 1. Virtual Windows Api-Sets and standard OS/Wine DLLs
            if dll_lower.startswith(("api-ms-win-", "ext-ms-win-")) or dll_lower in KNOWN_OS_LIBS:
                os_dlls.add(dll)
            # 2. Graphics APIs (DirectX, Vulkan, OpenGL)
            elif dll_lower in KNOWN_GRAPHICS_LIBS:
                gfx_libs.add(dll)
            # 3. Media Frameworks
            elif dll_lower in KNOWN_MEDIA_FRAMEWORKS or dll in detected_media:
                media_libs.add(dll)
            # 4. Known game-bundled software (Steam, EOS, DLSS, PhysX, etc.)
            elif dll_lower in KNOWN_GAME_BUNDLED_LIBS:
                game_bundled.add(dll)
            # 5. Unidentified dependencies (Potential missing runtimes)
            else:
                custom.add(dll)

        return os_dlls, game_bundled, custom, gfx_libs, media_libs

    def sanitize_custom_imports(self, raw_custom: set[str]) -> tuple[set[str], set[str]]:
        """
        Performs a final disk check on unidentified custom dependencies.
        
        If a custom DLL actually exists within the game directory, it is reclassified as 
        a local game DLL, added to self.game_bundled_dlls, and tracked in disk_found_custom_dlls 
        for potential debugging/fallback analysis.

        Returns:
            tuple[set[str], set[str]]: (cleaned_custom_dlls, disk_found_custom_dlls)
        """
        exe_dir = Path(self.exe_path).parent
        
        try:
            local_dlls = {f.name.lower() for f in exe_dir.rglob("*.dll") if f.is_file()}
        except Exception as e:
            logger.warning(f"Failed to scan directory {exe_dir} during custom sanitization: {e}")
            return raw_custom, set()

        cleaned_custom = set()
        disk_found_custom = set()

        for dll in raw_custom:
            dll_lower = dll.lower().strip()
            
            if dll_lower in local_dlls:
                disk_found_custom.add(dll)
                self.game_bundled_dlls.add(dll)
            else:
                cleaned_custom.add(dll)

        return cleaned_custom, disk_found_custom

    def verify_game_files_on_disk(self) -> set[str]:
        """Verifies if DLLs expected to be bundled with the game exist in the game directory."""
        exe_dir = Path(self.exe_path).parent
        missing = set()

        try:
            existing_files = {f.name.lower() for f in exe_dir.rglob("*") if f.is_file()}
        except Exception as e:
            logger.warning(f"Could not scan directory {exe_dir}: {e}")
            return missing

        for dll in self.game_bundled_dlls:
            if dll.lower() not in existing_files:
                missing.add(dll)

        if missing:
            logger.warning(f"[!] MISSING BUNDLED GAME FILES! Files not found on disk: {missing}")
        else:
            logger.info("[✓] All game-bundled DLLs found on disk.")

        return missing        

    def _detect_media_deps(self) -> set[str]:
        """Detects audio/video media frameworks from imports."""
        deps = set()
        if any(dll.startswith("xaudio") for dll in self.all_imports): 
            deps.add("xaudio")
        if "mfplat.dll" in self.all_imports: 
            deps.add("media_foundation")
        if "dsound.dll" in self.all_imports: 
            deps.add("directsound")
        return deps

    def _get_delay_imports(self) -> set[str]:
        """Extracts delay-loaded DLL imports if present in PE headers."""
        imports = set()
        if hasattr(self.pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
            for entry in self.pe.DIRECTORY_ENTRY_DELAY_IMPORT:
                if entry.dll:
                    try:
                        imports.add(entry.dll.decode("ascii").lower())
                    except UnicodeDecodeError:
                        pass
        return imports

    def _check_iat_integrity(self) -> bool:
        """
            Checks if the Import Address Table (IAT) exhibits structural anomalies 
            suggesting packing or obfuscation.
        """
        if not hasattr(self.pe, "DIRECTORY_ENTRY_IMPORT"):
            return True

        total = 0
        corrupted = 0
        for entry in self.pe.DIRECTORY_ENTRY_IMPORT:
            total += 1
            if entry.struct.OriginalFirstThunk == 0:
                corrupted += 1

        if total == 0:
            return True

        return (corrupted / total) > 0.3

    def detect_packer_name(self, db_path: str = "/home/theoddpirate/Downloads/packer.yar") -> str | None:
        """
            Matches PE sections against a YARA database 
            to identify packers/protectors (e.g., UPX, Themida).
        """
        if not os.path.exists(db_path):
            logger.warning(f"PEiD database file not found at: {db_path}")
            return None

        try:
            signatures = peutils.SignatureDatabase(db_path)
            matches = signatures.match(self.pe, ep_only=True)
            if matches:
                logger.info(f"Detected packer matches: {matches}")
                return matches[0]
        except Exception as e:
            logger.warning(f"Error matching packer database: {e}")

        logger.info("No packer or encryption detected.")
        return None  

    def check_pe_analyzable(self, exe_path: str) -> tuple[bool, str]:
        """
        Validates whether a PE executable can be analyzed safely 
        without failing due to corrupt headers, DRM protections, or heavy packing.

        Returns:
            tuple[bool, str]: (is_analyzable, status_reason)
        """
        try:
            pe = pefile.PE(exe_path, fast_load=True)
        except Exception as e:
            return False, f"PE header corrupt or unreadable ({e})"

        KNOWN_DRM_SECTIONS = {
            b".denuvo", b".vmp0", b".vmp1", b".themida", b".bind", 
            b"enigma", b".ecr", b".pyd", b".secure", b".aspack"
        }
    
        for section in pe.sections:
            sec_name = section.Name.rstrip(b"\x00").lower()
            if sec_name in KNOWN_DRM_SECTIONS:
                return False, f"Detected DRM/Protector section '{sec_name.decode(errors='ignore')}'"

        for section in pe.sections:
            if section.IMAGE_SCN_MEM_EXECUTE and section.SizeOfRawData > 0:
                data = section.get_data()
                if not data:
                    continue
                
                entropy = 0.0
                occurence = [0] * 256
                for byte in data:
                    occurence[byte] += 1
                for count in occurence:
                    if count > 0:
                        p = count / len(data)
                        entropy -= p * math.log2(p)

                if entropy > 7.3:
                    return False, f"High entropy ({entropy:.2f}) in executable section '{section.Name.decode(errors='ignore')}'"

        try:
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']
            ])
            
            imports_count = len(pe.DIRECTORY_ENTRY_IMPORT) if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT') else 0
            if imports_count == 0:
                return False, "Import Address Table (IAT) is empty or hidden"
            
        except Exception as e:
            return False, f"Failed to parse IAT ({e})"

        return True, "OK"

    def _get_architecture(self) -> str:
        """Detects binary architecture (x86, x64, arm64)."""
        machine = self.pe.FILE_HEADER.Machine
        if machine == 0x14c:
            return "x86"
        elif machine == 0x8664:
            return "x64"
        elif machine == 0xaa64:
            return "arm64"
        return "unknown"

    def _check_is_packed_or_encrypted(self) -> bool:
        """Calculates Shannon entropy across executable sections to detect packing/encryption."""
        for section in self.pe.sections:
            data = section.get_data()
            if not data or len(data) == 0:
                continue
            
            entropy = 0.0
            occurence = [0] * 256
            for byte in data:
                occurence[byte] += 1
            for count in occurence:
                if count > 0:
                    p = count / len(data)
                    entropy -= p * math.log2(p)

            if section.IMAGE_SCN_MEM_EXECUTE and entropy > 7.3:
                logger.warning(
                    f"High entropy ({entropy:.2f}) in section "
                    f"{section.Name.decode(errors='ignore')}. Likely packed/encrypted."
                )
                return True
        return False

    def _get_all_imports(self) -> set[str]:
        """Extracts all imported DLL names from the PE Import Table."""
        found = set()
        if hasattr(self.pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in self.pe.DIRECTORY_ENTRY_IMPORT:
                if entry.dll:
                    found.add(entry.dll.decode("utf-8", errors="ignore").lower())
        return found

    def _get_min_windows_version(self) -> str:
        """Extracts required minimum Windows version from subsystem headers."""
        try:
            major = self.pe.OPTIONAL_HEADER.MajorSubsystemVersion
            minor = self.pe.OPTIONAL_HEADER.MinorSubsystemVersion
            if major == 10: return "win10"
            if major == 6 and minor == 1: return "win7"
            if major == 5 and minor == 1: return "winxp"
            return f"win_v{major}.{minor}"
        except AttributeError:
            return "unknown"

    def _check_is_dotnet(self) -> bool:
        """Checks if the executable relies on the .NET framework."""
        try:
            com_descriptor = self.pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
            if com_descriptor.VirtualAddress != 0 and com_descriptor.Size != 0:
                return True
        except (IndexError, AttributeError):
            pass
            
        if not self.all_imports:
            self.all_imports = self._get_all_imports()
            
        return "mscoree.dll" in self.all_imports

    def _get_version_info(self) -> dict[str, str]:
        """Parses StringFileInfo structures from PE resources."""
        string_version_info = {}
        if hasattr(self.pe, "FileInfo") and self.pe.FileInfo:
            for fileinfo in self.pe.FileInfo[0]:
                if hasattr(fileinfo, "Key") and fileinfo.Key.decode(errors="ignore") == "StringFileInfo":
                    for st in fileinfo.StringTable:
                        for entry in st.entries.items():
                            key = entry[0].decode(errors="ignore")
                            val = entry[1].decode(errors="ignore")
                            string_version_info[key] = val
        return string_version_info

    def _determine_build_year(self) -> int | None:
        """Determines the build/release year based on PE timestamp or resource metadata."""
        try:
            ts = self.pe.FILE_HEADER.TimeDateStamp
            year = datetime.fromtimestamp(ts, tz=timezone.utc).year
            if 1995 <= year <= datetime.now(timezone.utc).year:
                return year
        except Exception:
            pass

        for value in self.version_info.values():
            match = re.search(r"\b(20\d{2}|19\d{2})\b", value)
            if match:
                return int(match.group(1))

        return None

