"""
PE Analyser Package.

Dette under-systemet håndterer analyse og prosessering av PE-filer (Portable Executables).

Eksempel på bruk:
    >>> from pe_analyser import analyse_pe_file
    >>> result = analyse_pe_file("path/to/file.exe")
"""

# Importer de viktigste funksjonene/klassene fra underfilene
# slik at brukeren slipper å importere fra dype stier (f.eks. pe_analyser.analyser)
from .PEanlyser import PEanalyser

# __all__ definerer eksplisitt hva som eksporteres når noen kjører:
# `from pe_analyser import *`
# Det er også god praksis for å hjelpe IDE-er og linting-verktøy.
__all__ = [
    "PEanalyser",
]
