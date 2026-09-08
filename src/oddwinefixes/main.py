import sys
import os
from oddwinefixes.pe_analyser import  PEanalyser
from oddwinefixes.wine_analyser import WineEnvironment, DynamicWinetricksMapper, WineTester
from oddwinefixes.utils import prioritize_verbs_by_year
from oddwinefixes.const import DEBUG, NAME, DESCRIPTION, VERSION, AUTHOR, LICENSE
from oddwinefixes.utils.logger import get_logger, setup_logging
logger = get_logger("main")




def main():
    setup_logging(verbose=False)
    logger.info(f"Welcome to {NAME} v{VERSION} by {AUTHOR}")
    logger.info(f"{DESCRIPTION}")
    logger.info(f"License: {LICENSE}")
    if DEBUG:
        prefix_path = "/home/theoddpirate/Games/Heroic/Prefixes/ELDEN RING"
    else:
        prefix_path = input("Enter WINEPREFIX path: ").strip()
    if DEBUG:
        exe_path = "/mnt/Games/SteamLibrary/steamapps/common/Crimson Desert/bin64/CrimsonDesert.exe"
    else:
        exe_path = input("Enter EXE path: ").strip()

    logger.info("[+] Gattering data about the prefix and wine/proton usage....")
    wine_env = WineEnvironment(prefix_path)
    mapper = DynamicWinetricksMapper(wine_env)
    logger.info(f" - Detected Wine/Proton version: {wine_env.proton_version}")
    logger.info(f" - Installed at: {wine_env.proton_root}")
    logger.info(f" - Version: {mapper.windows_version}")
    tester = WineTester(wine_env, mapper)

    logger.info("[+] Scanning PE file for dependencies and buildin....")
    analyser =  PEanalyser(exe_path,False)
    logger.info(f" - Detected build year: {analyser.build_year}")
    missing_packages = {}
    already_fulfilled = []
    logger.info(f"[+] Checking prefix for missing dependencies for: {', '.join(analyser.custom_dlls)}")

    for dll in analyser.custom_dlls:
        candidates = mapper.resolve_dll(dll)
        if not candidates:
            continue

        installed_candidates = [c for c in candidates if c in mapper.installed_verbs]
        not_installed_candidates = [
            c for c in candidates if c not in mapper.installed_verbs
        ]
        print("")
        logger.info(f"[+] Analyzing {dll}:")
        logger.info(f" - Installed in prefix: {installed_candidates if installed_candidates else 'None'}")
        logger.info(f" - Available options in Winetricks: {', '.join(not_installed_candidates)}")

        if installed_candidates:
            already_fulfilled.append(
                (dll, installed_candidates, not_installed_candidates)
            )
        else:
            missing_packages[dll] = not_installed_candidates
    print("")
    for dll, verbs in missing_packages.items():
        sorted_verbs = mapper.prioritize_verbs_by_year(verbs, analyser.build_year)
        missing_packages[dll] = sorted_verbs

    if already_fulfilled and not missing_packages:
        
        logger.info("[+] All detected DLLs already have a matching runtime installed:")
        for dll, installed, _ in already_fulfilled:
            logger.info(f" - {dll} -> Found in prefix: {', '.join(installed)}")

        if tester.run_and_check(exe_path):
            logger.info("[+] Application launched successfully with existing dependencies!")
            return
        else:
            logger.info("[-] Application failed to run despite existing runtimes.")
            logger.info("[-] Adding uninstalled alternatives to candidate queue...")
            for dll, _, not_installed in already_fulfilled:
                missing_packages[dll] = not_installed

    if not missing_packages:
        logger.info("[+] No external runtime dependencies detected to install.")
        tester.run_and_check(exe_path)
        return

    logger.info("Missing/Alternative candidate packages:")
    for dll, verbs in missing_packages.items():
        logger.info(f" - {dll} -> Available verbs: {', '.join(verbs)}")

    choice = (
        input("Run (A)uto-retry mode or (M)anually select versions? [A/m]: ")
        .strip()
        .lower()
    )

    if choice in ["", "a", "auto"]:
        sorted_missing = sorted(missing_packages.items(), key=lambda x: len(x[1]))
        for dll, verbs in sorted_missing:
            success = False
            for verb in verbs:
                mapper.install_verb(verb)
                if tester.run_and_check(exe_path):
                    logger.info(f"[+] Success! {verb} resolved dependencies for {dll}.")
                    success = True
                    break
                else:
                    logger.info(f"[-] {verb} failed to fix execution.")

            if not success:
                logger.info(f"[!] Could not find a working package for {dll}.")
    elif choice in ["m", "manual"]:
        logger.info("=== Manual Verb Selection ===")

        sorted_missing = sorted(missing_packages.items(), key=lambda item: len(item[1]))

        for dll, verbs in sorted_missing:
            logger.info(f"--------------------------------------------------")
            logger.info(f"DLL: {dll}")
            logger.info(f"Available Winetricks verbs:")

            for idx, verb in enumerate(verbs, 1):
                logger.info(f"  [{idx}] {verb}")

            logger.info("  [s] Skip this DLL")
            logger.info("  [q] Quit manual selection")

            while True:
                user_input = (
                    input(f"Select a verb for {dll} (1-{len(verbs)} / s / q): ")
                    .strip()
                    .lower()
                )

                if user_input == "q":
                    logger.info("[!] Cancelling manual selection.")
                    return

                if user_input in ["s", "skip"]:
                    logger.info(f"[*] Skipped {dll}.")
                    break

                if user_input.isdigit():
                    selection = int(user_input)
                    if 1 <= selection <= len(verbs):
                        selected_verb = verbs[selection - 1]
                        logger.info(f"[->] Installing selected verb: {selected_verb}...")

                        mapper.install_verb(selected_verb)

                        if tester.run_and_check(exe_path):
                            logger.info(
                                f"[+] Application started successfully with {selected_verb}!"
                            )
                            break

                        else:
                            logger.info(
                                f"[-] Application failed or still had issues after installing {selected_verb}."
                            )
                        
                else:
                    logger.info("[-] Invalid selection, please try again.")


if __name__ == "__main__":
    main()
