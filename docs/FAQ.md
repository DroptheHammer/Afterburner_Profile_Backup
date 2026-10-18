# Frequently Asked Questions

Short answers to common questions about Afterburner Profile Backup.

## Where are my profiles?

MSI Afterburner keeps your profiles in a folder named `Profiles`. That folder
is inside the Afterburner folder. It is usually here:

`C:\Program Files (x86)\MSI Afterburner\Profiles`

The app finds this folder for you the first time you open it. It shows you the
list and asks "Is this correct?". If it guessed wrong, click
"No, let me pick the folder".

Your backups go into the backup folder you choose. Each backup gets its own
dated folder, like `D:\Backups\Afterburner\2026-10-18_14-03-22`.

[SCREENSHOT: First run screen showing the list of profiles found]

## Will this change my settings?

Backing up does not change anything in Afterburner. It only makes copies.

Restoring does replace the profiles you pick. Before it does that, the app
makes a safety copy of your current profiles. The safety copy is saved in a
folder named `before-restore` inside your backup folder. Nothing is deleted.

Not sure? Tick "Test run (don't change anything)" on the home screen. The app
then shows what would happen, and copies nothing.

[SCREENSHOT: Home screen with the Test run box ticked]

## Do I need to close Afterburner?

For a backup: no.

For a restore: yes. Afterburner can write over restored profiles when it
closes. The app notices if Afterburner is open. It asks if you want it closed.

1. Click "Close Afterburner for me". Or click "I'll close it myself".
2. If you close it yourself, right-click its icon near the clock.
3. Choose Exit.
4. Click "Restore Selected Profiles" again.

[SCREENSHOT: The "Afterburner is still open" question]

## Does it work with a NAS?

Yes. A NAS is a small storage box on your home network.

1. Make sure the NAS is turned on and connected.
2. Click "Back Up My Profiles".
3. Click "Choose Folder…".
4. Pick a folder on the NAS.

You can pick a mapped drive (like a drive letter) or a network folder like
`\\NAS\share\AfterburnerBackups`. If you pick a mapped drive, the app saves it
as the network folder form. This way it still works after the Windows
permission prompt that appears when you restore.

If the NAS can't be reached, see TROUBLESHOOTING.md.

## Why does Restore ask for administrator permission?

Windows protects the Afterburner folder. Only an administrator can put files
back into it.

1. Click "Restore Profiles".
2. The app explains why it needs permission.
3. Click "Continue".
4. Windows asks for permission. Click Yes.

The app restarts and opens the restore screen. Backing up never needs this
permission.

[SCREENSHOT: The "Administrator permission needed" message]

## Will profiles work on a different graphics card?

Only the numbered profiles (`Profile1.cfg` to `Profile5.cfg`) are general.

Some profile files have a long name starting with `VEN_`. These belong to one
graphics card in one slot. They only apply to the same card in the same slot.
If you change your graphics card, those files will not apply to the new one.

The app still backs up every profile, so nothing is lost.

## Where are settings and logs kept?

The app keeps its own small files here:

`%LOCALAPPDATA%\AfterburnerProfileBackup`

To open it:

1. Press the Windows key and the R key together.
2. Type `%LOCALAPPDATA%\AfterburnerProfileBackup`.
3. Press Enter.

You will see `settings.json` (your folder choices) and `log.txt` (what the app
did). You can also open the log from "Settings", using "Open Log File".

The log never contains the contents of your profiles.

## Does it send any data?

No. The app never uses the internet. It has no tracking.

It only writes to three places:

1. The backup folder you chose.
2. The Afterburner folder, only during a restore you confirmed.
3. Its own settings folder, shown above.

It is free and open source (MIT License).

## Is this made by MSI?

No. This app is not affiliated with or endorsed by MSI or the authors of MSI
Afterburner or RivaTuner. Use it at your own risk, and test a restore before
you rely on it.
