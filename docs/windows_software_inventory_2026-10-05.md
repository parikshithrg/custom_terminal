# Windows software inventory — 05-Oct-26

This is a practical reinstall checklist captured from Windows installed-program
records before the Linux migration. It is not a licence record and cannot
reliably identify the person who installed a program. The categories below are
best-effort classifications based on vendor, type, and recorded installation
date.

## Likely user-installed or deliberately added

| Software | Version | Publisher | Recorded installation date |
| --- | --- | --- | --- |
| AIDA64 Extreme | 8.20 | FinalWire Ltd. | 09-Sep-26 |
| CPUID CPU-Z MSI | 2.19 | CPUID, Inc. | 09-Sep-26 |
| Git | 2.55.0.3 | The Git Development Community | 10-Sep-26 |
| Google Chrome | 154.0.8037.95 | Google LLC | 05-Oct-26 |

## Likely pre-installed Windows, motherboard, driver, or peripheral software

| Software | Version | Publisher |
| --- | --- | --- |
| Intel Chipset Device Software | 10.1.20062.8627 | Intel |
| Intel Management Engine Components | 2541.8.41.0 | Intel |
| Intel Serial IO | 30.100.2417.30 | Intel |
| MSI Center SDK | 3.2026.0810.01 | MSI |
| OnScreen Control | 9.47.0.0 | LG Electronics |
| Realtek Audio Driver | 6.0.9998.1 | Realtek Semiconductor |
| Realtek Ethernet Controller Driver | 10.79.50.1003 | Realtek |

## Windows/Microsoft components recorded as installed apps

| Software | Version | Notes |
| --- | --- | --- |
| Microsoft Edge | 154.0.4258.53 | Windows browser component |
| Copilot | 154.0.4258.53 | Microsoft application/component |
| Microsoft Visual C++ 2015–2022 Redistributable (x64) | 14.36.32532.0 | Runtime dependency |
| Microsoft Visual C++ 2015–2022 Redistributable (x86) | 14.36.32532.0 | Runtime dependency |
| Microsoft Windows Application Compatibility Fix Database | — | Windows compatibility component |

## Important inventory limitation

Windows denied access to the Store/AppX package inventory during this capture.
Consequently, this list may omit Microsoft Store applications and some
per-user-installed apps. Before erasing Windows, manually check the Start menu
and Settings → Apps → Installed apps for anything not represented here,
especially password managers, VPNs, cloud-sync clients, paid creative tools,
and any hardware-control utility you want to retain.

For the Linux installation, the likely useful reinstalls are Git, a browser,
the ChatGPT desktop app, and any owner-selected hardware-monitoring utilities.
The Windows-only driver/control items above should generally not be reinstalled
on Linux; Linux uses its own kernel drivers and vendor tooling where required.
