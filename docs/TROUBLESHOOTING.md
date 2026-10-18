# Troubleshooting

Find your problem below and follow the numbered steps.

## We can't find my profiles

The app looks for MSI Afterburner in the usual places. If it can't find it,
you can show it where it is.

1. Open the app. On the first screen, click "No, let me pick the folder".
   (Already set up? Click "Settings", then "Find it again automatically".)
2. Pick the MSI Afterburner folder. It is usually
   `C:\Program Files (x86)\MSI Afterburner`.
3. The folder must contain a folder named `Profiles`. If it doesn't, the app
   says "That folder doesn't look like MSI Afterburner".
4. Check that the list shows your profiles. Click "Yes, that's right".

Still no profiles? Open MSI Afterburner once, save a profile, and try again.

[SCREENSHOT: Picking the Afterburner folder]

## My NAS or backup folder can't be reached

You may see: "We can't reach this folder."

1. Check the NAS is turned on and connected to your network.
2. Open File Explorer and try to open the NAS folder yourself.
3. If you can't open it there, fix that first (cable, Wi-Fi, NAS power).
4. In the app, click "Back Up My Profiles", then "Choose Folder…", and pick
   the folder again.

**Mapped drive or network folder?**
A mapped drive is a network folder with a drive letter. A network folder
looks like `\\NAS\share\AfterburnerBackups`.

When you restore, Windows asks for permission and the app restarts. A
restarted app can sometimes not see a mapped drive letter. For this reason
the app saves the network folder form instead of the letter. If your backup
folder is not found after restoring:

1. Click "Settings".
2. Next to "Backup folder:", click "Change…".
3. Pick the folder using the network form, such as `\\NAS\share\AfterburnerBackups`.

## Windows says "Windows protected your PC"

This is Windows SmartScreen. It shows for apps that are new or not signed.
This app is free, so it is not signed with a paid certificate. The warning
does not mean the app is bad.

First, check where you got the file. Download it only from the project's
GitHub Releases page.

If you downloaded it from there:

1. On the blue "Windows protected your PC" window, click "More info".
2. Click "Run anyway".

[SCREENSHOT: SmartScreen window with the More info link]

## My antivirus blocks the app or says it is a threat

Some antivirus programs warn about apps that are unsigned and unpack
themselves when they start. This app works that way, so it can trigger a
false alarm.

1. Check the file came from the project's GitHub Releases page.
2. If your antivirus quarantined it, open the antivirus and restore the file.
3. If it asks, allow the app, or add it to the allowed list.
4. If you are not comfortable, don't run it. You can build it yourself from the
   source code. See DEVELOPER.md.

## I restored, but nothing seems to have changed

Check these in order.

1. **Was Afterburner open?** If so, it may have written over the restored
   profiles when it closed. Close Afterburner (right-click its icon near the
   clock, choose Exit). Then restore again.
2. **Did you open Afterburner again?** Start it again after restoring. Then
   click the profile button to apply it.
3. **Is a startup profile set?** If Afterburner applies settings when Windows
   starts, the restored profile may apply the next time you start your PC.
4. **Is it a different graphics card?** Profile files starting with `VEN_` only
   work with the same card in the same slot. The numbered profiles
   (`Profile1.cfg` to `Profile5.cfg`) are general.
5. **Did you pick the right profiles?** On the restore screen, check the
   ticks before clicking "Restore Selected Profiles".

Your earlier profiles are safe. The app saves them in a `before-restore`
folder inside your backup folder before it changes anything.

## "We can't write to the Afterburner folder"

Restoring needs administrator permission. Windows protects that folder.

1. Close the app.
2. Open it again and click "Restore Profiles".
3. Click "Continue" when the app explains.
4. When Windows asks for permission, click Yes.

If you clicked No, the app says "Windows permission was not given". You can
still make backups. Try Restore again when you are ready.

Still stuck? Check you are signed in to Windows with an administrator
account. Ask the owner of the PC if you are not sure.

## Where can I see what the app did?

1. Click "Settings".
2. Click "Open Log File".

The log is in `%LOCALAPPDATA%\AfterburnerProfileBackup`. If you ask for help,
you can share the lines from the log. They don't contain your profile
contents.

## Something went wrong and I'm worried

Nothing is ever deleted by this app. Your original profiles and your backups
stay where they are. Details of the problem are saved in the log file.
