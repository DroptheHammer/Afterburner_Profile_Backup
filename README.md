# Afterburner Profile Backup

A free, simple Windows app that keeps a safe copy of your MSI Afterburner profiles and puts them back when you need them.

[SCREENSHOT: Home screen with the two big buttons]

## Who is it for?

Gamers who tweak their graphics card with MSI Afterburner and do not want to lose their profiles after a Windows reinstall, a driver problem, or a mistake. You do not need any technical skills.

## Download and run in 3 steps

1. Go to the Releases page: https://github.com/DroptheHammer/afterburner-profile-backup/releases and download AfterburnerProfileBackup.exe from the newest release.
2. Save the file anywhere you like, for example on your desktop. There is nothing to install.
3. Double-click AfterburnerProfileBackup.exe. The first time, click "Yes, that's right" when it shows your Afterburner profiles.

[SCREENSHOT: First screen asking "Is this correct?" with the list of profiles]

Windows may show a blue "Windows protected your PC" box because the app is free and not signed. See the Troubleshooting guide for what to do.

## What can it do?

- "Back Up My Profiles" copies your profiles into a new dated folder. You choose where: another drive, or a NAS such as \\NAS\share\AfterburnerBackups.
- "Restore Profiles" puts profiles from an earlier backup back into Afterburner. You choose which ones.
- "Test run (don't change anything)" shows what would happen without copying anything.

[SCREENSHOT: Backup screen showing the green Done message]

## Is it safe?

- Nothing is ever deleted. Old backups are never replaced.
- Making a backup does not change Afterburner at all.
- Before every restore, the app makes a safety copy of your current profiles. It is kept in a folder called before-restore inside your backup folder.
- Every copied file is checked to make sure it matches the original.
- Restoring asks for administrator permission, because Windows protects the Afterburner folder. Backups do not need it.
- Nothing is sent over the internet. No data ever leaves your PC.

## Your first backup

Follow the [Quick Start guide](docs/QUICKSTART.md). It has numbered steps for your first backup, your first restore, and a test run. The same guide is inside the app under "Help".

## More help

- [Quick Start](docs/QUICKSTART.md)
- [FAQ](docs/FAQ.md) - common questions
- [Troubleshooting](docs/TROUBLESHOOTING.md) - when something does not work
- [For developers](docs/DEVELOPER.md) - building the app from the source code

## Disclaimer

This app is not affiliated with or endorsed by MSI or the authors of MSI Afterburner or RivaTuner. It only copies your own files and does not include any part of Afterburner. Use it at your own risk, and test a restore before you rely on it.

## License

MIT License. The app is free and open source. You can use, copy and share it. See the LICENSE file.
