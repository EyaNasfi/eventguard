---
title: EventGuard — Development environment
author: Aya NASFI
updated: 2026-11-02
---

# Development environment

## Machine (detected 2026-11-02)

| Item | Value |
|---|---|
| OS | Windows 11 Pro 26H2, build 10.0.26300.9457 (repair-installed 2026-11-04; was 25H2, 26200.8246) |
| CPU | Intel Core i5-10500H, virtualisation enabled in firmware |
| Hypervisor / WSL2 | Active since 2026-11-04 (see the incident below): WSL 2.7.14.0, default version 2 |
| RAM | 11.8 GB |
| Free disk | C: 29.7 GB, D: 111.8 GB |
| Package manager | winget (available) |
| Project path | `D:\OneDrive\Bureau\PFE` (inside OneDrive, see note below) |

Target setup: **Windows + WSL2 backend + Docker Desktop**.

## Incident 2026-11-02: `wsl --install` → "The system cannot find the path specified"

Diagnosis (read-only checks): the Store package `MicrosoftCorporationII.WindowsSubsystemForLinux` 2.6.1 is registered, but `C:\Program Files\WSL\wsl.exe` is missing. The inbox `wsl.exe` (10.0.26100.1424) forwards to that path, so every `wsl` command fails. The `LxssManager` and `vmcompute` services are absent: the optional features *Windows Subsystem for Linux* and *Virtual Machine Platform* are not enabled. No distribution is registered, so there is nothing to lose. Fix: remove the broken package, enable both features with DISM, reboot, reinstall WSL from Microsoft's official winget package (`Microsoft.WSL`). Steps were given to Aya; the result goes here.

**2026-11-03, result:** the broken package was removed, but both DISM `/enable-feature` commands failed with **Error 14098, "The component store has been corrupted"** (`dism.log`: `CBS HRESULT=0x80073712` = ERROR_SXS_COMPONENT_STORE_CORRUPT). This is a Windows servicing problem, independent of WSL. Fix in progress: `DISM /Online /Cleanup-Image /RestoreHealth` (repairs the store from Windows Update), then `sfc /scannow`, reboot, and retry the two features. Fallback if RestoreHealth fails: Settings → System → Recovery → "Fix problems using Windows Update" (reinstalls Windows in place, keeps files and apps).

**2026-11-03, repair done:** `RestoreHealth` → "The restore operation completed successfully" (about 1 h 30, with a long phase around 64–70%). `sfc /scannow` → "found corrupt files and successfully repaired them". Next: reboot, then enable the two WSL features again.

**2026-11-03 17:00, still failing after the reboot (16:56):** both `/enable-feature` commands return 14098 again. `CBS.log` names the broken items: *Component metadata corrupt* (`CorruptManifest`) for the **not yet installed** Hyper-V payload components, e.g. `HyperV-VID-Deployment-LanguagePack`, `HyperV-Networking-merged-Deployment-LanguagePack`, `Undocked-Hypervisor-Host-Service-Deployment-LanguagePack` (cultures en-US, fr-FR, ar-SA, versions 10.0.26100.4066–7705). `RestoreHealth` and `sfc` only repair *installed* components, so they cannot fix these, and CBS logs "Automatic corruption repair has already been attempted today". **Next fix:** an in-place repair reinstall (Settings → System → Recovery → "Fix problems using Windows Update" → Reinstall now), which rewrites the whole component store and keeps files and apps. **Update:** "Fix problems using Windows Update" shows *"This option is currently unavailable"*. Facts checked: Windows 11 Pro 25H2, build 26200.8246, **install language fr-FR (040C)** with an en-US display language, no pending reboot, no Windows Update policy, 38.7 GB free on C:. Next: (1) install every pending update and retry that option; (2) otherwise run a repair install from the official Windows 11 ISO, **French, x64**, using setup.exe with "Keep personal files and apps". The ISO language must match the install language, or the "keep" option is greyed out. **Windows Update itself fails:** the System log (WindowsUpdateClient, event 20) shows the *Windows 11, version 25H2* feature update failing five times between 2 and 3 Nov: `0x80070057` (twice), `0x800704C7`, `0xC190020E` (not enough disk space at that time) and `0x80073712` (corrupt store). Last cumulative update installed: KB5127690 (15 Oct 2026). Decision: skip Windows Update and go straight to the ISO repair install (option B), with the ISO saved on D:. Simpler first try: the agent downloaded the official **Windows 11 Installation Assistant** (`go.microsoft.com/fwlink/?linkid=2171764`) to `C:\Users\Eya\Downloads\Windows11InstallationAssistant.exe`: 4 MB, version 1.4.19041.7779, Authenticode **Valid**, signed by Microsoft Corporation. Aya runs it herself (UAC, reboots). If it refuses or fails, fall back to the French x64 ISO.

**2026-11-04, repair install done.** The Installation Assistant first asked for PC Health Check: the agent downloaded the official MSI (`aka.ms/GetPCHealthCheckApp`, 13.7 MB, Authenticode Valid, Microsoft Corporation) and Aya installed it. The reinstall finished at 18:00. Result: **Windows 11 Pro 26H2, build 26300.9457**; files, apps and the project venv kept; `C:\Windows.old` present (rollback possible for 10 days); C: free space down to 20.3 GB. WSL features not yet enabled. Next: the two `dism /enable-feature` commands.

**2026-11-04, resolved.** Aya enabled both features, rebooted and installed WSL with winget. Checked by the agent (boot 22:36): `HypervisorPresent = True`; `vmcompute` and `WslService` running; `wsl --version` → **WSL 2.7.14.0**, kernel 6.18.33.2-2, WSLg 1.0.73.2; `wsl --status` → **default version 2**. No distribution installed, which is expected because Docker Desktop brings its own. **A1 done.** **Plan B** if the PC still cannot run WSL2/Hyper-V: run the Docker lab on another Linux host (a cloud VM or GitHub Codespaces) and keep this PC for editing. That would need a decision from the project lead.

## Tool versions

| Tool | Version | Source | Status |
|---|---|---|---|
| Python | 3.12.10 (project venv `.venv`) | python.org (pre-installed) | OK |
| pre-commit | 4.3.0 (in `.venv`) | PyPI | OK |
| fastapi / sqlmodel / pydantic | 0.162.0 / 0.0.48 / 2.14.2 | PyPI, pinned in `pyproject.toml` | OK |
| Git | 2.56.0.windows.4 | git-for-windows (GitHub release), winget `Git.Git`, hash verified | OK (2026-11-04) |
| WSL2 | 2.7.14.0 (kernel 6.18.33.2-2) | Microsoft, winget `Microsoft.WSL` | OK (2026-11-04) |
| Docker Desktop + Compose | Docker 29.9.2 (build a82e528), Compose v5.6.1, WSL 2 backend, data on `D:\Docker` | docker.com (signed installer, Docker Inc) | OK (2026-11-04): `hello-world` passed |
| gitleaks | 8.30.1 (pre-commit hook pins v8.28.0, CI uses gitleaks-action v2) | github.com/gitleaks release, winget `Gitleaks.Gitleaks`, hash verified | OK (2026-11-04): working tree → "no leaks found" |
| GitHub CLI | 2.103.3 | github.com/cli release, winget `GitHub.cli`, hash verified | OK (2026-11-04) |

## Git settings

- `user.name = Aya NASFI`; `user.email` = provided by Aya. Set **per repository** (`git config`, not `--global`).
- 2026-11-04: `git init -b main` done, `pre-commit install` done.
- 2026-11-05: baseline commit `c5cea87` + tag `sprint-0`; remote `origin = https://github.com/EyaNasfi/eventguard.git` (private), pushed by Aya. `gh auth setup-git` makes Git use the gh login (account EyaNasfi, keyring).
- The pre-commit gitleaks hook uses the installed binary, not the upstream hook (which downloads Go). See `.pre-commit-config.yaml`.

## Gemini (2026-11-05)

- Free-tier key from Google AI Studio, stored only in `.env` (53 characters; never printed or logged).
- `GEMINI_MODEL = gemini-3.5-flash`. On 2026-11-05 the API listed 22 Flash models for this key (2.5 → 3.8, plus `-latest` aliases and previews). `gemini-3.8-flash` gave 503 (high demand) twice. Aliases (`gemini-flash-latest`) and `-preview` models are avoided for reproducibility.
- The API reported `model_version = gemini-3.6-flash` for a `gemini-3.5-flash` request, so the served version must be logged on every run.

## Avast HTTPS scanning (2026-11-05)

Avast Web Shield intercepts HTTPS: the certificate presented for `generativelanguage.googleapis.com` was issued by "Avast Web/Mail Shield Root". Windows trusts that root but Python (certifi) does not, which gives `SSL: CERTIFICATE_VERIFY_FAILED`. Fix: Aya added the Avast exceptions `https://generativelanguage.googleapis.com/*` and `https://api.github.com/*`. After that, the certificate came from Google Trust Services (WE2). If pip, Docker builds or gh fail with TLS errors, check Avast first.

**More Avast exceptions (2026-11-05, S1-02).** `pip install mcp` failed with `Connection broken: InvalidChunkLength`: Avast was intercepting `pypi.org` and `files.pythonhosted.org` too. Aya added the exceptions `https://pypi.org/*`, `https://files.pythonhosted.org/*`, `https://github.com/*`, `https://registry-1.docker.io/*`, `https://auth.docker.io/*` and `https://production.cloudflare.docker.com/*`, which makes 8 in total. After that, the certificates came from GlobalSign and the install worked.

**Avast breaks loopback HTTP to `/mcp` (2026-11-05).** Any request to `127.0.0.1` whose path ends in a `/mcp` segment (`/mcp`, `/MCP`, `/mcp/`, `/x/mcp`) gets a broken reply on the host: `transfer-encoding: chunked`, no body, then a reset or a timeout. The server sent a correct response (traced at the ASGI level). It reproduces with a minimal ASGI app, while `/mcpx`, `/tools` and `/sse` are fine. Avast's firewall and IDS (`afwServ`, `aswidsagent`) are running. Traffic between containers is **not** affected (verified with an MCP client inside the gateway container). Consequences:
- host-side gateway tests use in-memory ASGI transports;
- do not try to reach the gateway from Windows. Its port is not published anyway (SR-14).

## Network note (2026-11-05)

A virtual adapter ("Connexion au réseau local 2") uses DNS `198.18.0.1/2`, which is typical of a VPN or proxy tool in fake-IP/TUN mode. Some names fail to resolve now and then: `go.dev` (pre-commit), `api.github.com` (`gh run list`), and direct DNS queries time out. `git push` to github.com works. If gh or pip fail with a connection error, turn off the VPN/proxy and retry. The agent shell cannot use the gh login (keyring), so Aya runs `gh` and reads the CI status on github.com.
- `core.autocrlf = input` on Windows. Files are committed with LF and the working tree is not converted, so shell scripts and Dockerfiles stay valid inside Linux containers. `.gitattributes` forces `eol=lf` for text files as a second guard.

## Note on OneDrive

The project lives in a OneDrive-synced folder. Syncing `.venv`, `data/` and Docker bind mounts can lock files and slow down builds. Recommended: pause OneDrive sync for this folder, or move the clone to `D:\dev\eventguard`. The clean-machine test (Step 2) uses a fresh clone outside OneDrive.
