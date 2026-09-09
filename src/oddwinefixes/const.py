import os
import re

# Main name used in the app
NAME = "OddWineFixes"
DESCRIPTION = "A PE Analyser and Wine/Proton missing dependency/font fixer"
VERSION = "0.0.1"
AUTHOR = "TheOddPirate"
LICENSE = "LGPL-2.1-or-later"
DEBUG = True

KNOWN_OS_LIBS = {
    # System & Core
    "kernel32.dll", "kernelbase.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "version.dll", "winmm.dll", "ucrtbase.dll",
    "ntdll.dll", "comctl32.dll", "ws2_32.dll", "shlwapi.dll", "rpcrt4.dll",
    "imm32.dll", "bcrypt.dll", "crypt32.dll", "setupapi.dll", "hid.dll",
    "iphlpapi.dll", "winhttp.dll", "wininet.dll", "pdh.dll", "psapi.dll",
    "gdiplus.dll", "secur32.dll", "userenv.dll", "dwmapi.dll", "uxtheme.dll",
    # Graphics & DirectX (Rendres av Wine / DXVK / VKD3D)
    "d3d11.dll", "d3d12.dll", "dxgi.dll", "d3d9.dll", "d3dcompiler_43.dll",
    "d3dcompiler_47.dll", "xinput1_4.dll", "xinput1_3.dll", "xaudio2_7.dll",
    "opengl32.dll", "vulkan-1.dll",

    # Media Frameworks
    #"mfplat.dll", "mf.dll", "mfreadwrite.dll", 
    "dxva2.dll", "dsound.dll"
}
KNOWN_GRAPHICS_LIBS = {
     # Graphics & DirectX (Rendres av Wine / DXVK / VKD3D)
    "d3d11.dll", "d3d12.dll", "dxgi.dll", "d3d9.dll", "d3dcompiler_43.dll",
    "d3dcompiler_47.dll", "xinput1_4.dll", "xinput1_3.dll", "xaudio2_7.dll",
    "opengl32.dll", "vulkan-1.dll",
}

KNOWN_MEDIA_FRAMEWORKS = {
    # Media Frameworks
    "mfplat.dll", "mf.dll", "mfreadwrite.dll", "dxva2.dll", "dsound.dll"
    
    }
KNOWN_GAME_BUNDLED_LIBS = {
    "steam_api64.dll", "steam_api.dll", "eossdk-win64-shipping.dll", "galaxy64.dll",

    "sl.interposer.dll", "sl.common.dll", "sl.dlss.dll", "sl.reflex.dll",
    "libxess.dll", "libxess_fg.dll", "libxell.dll",
    "amd_ags_x64.dll", "amd_fidelityfx_loader_dx12.dll", "nvngx.dll",

    "sentry.dll", "bink2w64.dll", "fmod.dll", "fmodstudio.dll", "libpng18.dll"
}


WINDOWS_VERSION_MAP = {
    "win11": "Windows 11",
    "win10": "Windows 10",
    "win81": "Windows 8.1",
    "win8": "Windows 8",
    "win2008r2": "Windows 2008 R2",
    "win7": "Windows 7",
    "win2008": "Windows 2008",
    "vista": "Windows Vista",
    "win2003": "Windows 2003",
    "winxp64": "Windows XP 64",
    "winxp": "Windows XP",
    "win2k": "Windows 2000",
    "winme": "Windows ME",
    "win98": "Windows 98",
    "win95": "Windows 95",
    "nt40": "Windows NT 4.0",
    "nt351": "Windows NT 3.51",
    "win31": "Windows 3.1",
    "win30": "Windows 3.0",
    "win20": "Windows 2.0",
}
# Used by helper.py to sort posible matches based on PE build year
DOTNET_RELEASE_MAP = {
    "dotnet11": 2003,
    "dotnet20": 2005,
    "dotnet30": 2006,
    "dotnet35": 2008,
    "dotnet40": 2010,
    "dotnet45": 2012,
    "dotnet46": 2015,
    "dotnet47": 2017,
    "dotnet48": 2019,
    "dotnet6": 2021,
    "dotnet7": 2022,
    "dotnet8": 2023,
    "dotnet9": 2024,
}
# Used by the wine log analyser
LOG_PATTERNS = {
"missing_dll": re.compile(
    r"import_dll.*?Library\s+([^\s()]+\.dll).*?needed by L\"[^\"]*?\\([^\"\\]+\.(?:exe|dll))\"",
    re.IGNORECASE,
),
    "font_issue": re.compile(
        r"(?:dwrite|gdi32|freetype).*?(?:font|SelectObject|CreateFont)|FontFamily|System\.Drawing\.Font|CreateFontIndirect|get_Font|gdiplus",
        re.IGNORECASE,
    ),
    "entrypoint_missing": re.compile(
        r"err:module:find_forwarded_export\b.*?symbol\s+[\"']?(.*?)[\"']?\s+not found",
        re.IGNORECASE,
    ),

    "nvidia_issue": re.compile(
        r"(?:nvapi64?|nvml|nvwgf2um64|nvoptix|nvcuda|sl\.dlss|sl\.common).*?(?:failed|not found|disabled|error)",
        re.IGNORECASE,
    ),
    "amd_issue": re.compile(
        r"(?:amd_ags_x64|amd_fidelityfx|atig6pxx|atig6txx).*?(?:failed|not found|disabled|error)",
        re.IGNORECASE,
    ),
    "graphics_runtime_error": re.compile(
        r"(?:vulkan|vkd3d|dxvk).*?(?:VK_ERROR_|failed to create device|instance creation failed|driver missing)",
        re.IGNORECASE,
    ),
}