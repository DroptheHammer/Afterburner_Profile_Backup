# Quick Start

This guide shows you how to back up your MSI Afterburner profiles and how to put them back. It takes about five minutes.

# Before you start

- You do not need to install anything. Just double-click the file AfterburnerProfileBackup.exe.
- Making a backup never changes Afterburner.
- Putting profiles back (restoring) needs administrator permission. Windows will ask you. This is normal.
- Nothing is ever deleted. Before every restore, the app makes a safety copy of your current profiles.

# Step 1: Open the app for the first time

1. Double-click AfterburnerProfileBackup.exe.
2. The app looks for MSI Afterburner on your PC.
3. You will see the question "We found your Afterburner profiles here. Is this correct?" with a list of your profiles.
4. If the folder looks right, click "Yes, that's right".
5. If it is wrong, click "No, let me pick the folder". Choose your MSI Afterburner folder. It is usually in Program Files (x86). It must contain a folder named Profiles.

[SCREENSHOT: First screen asking "Is this correct?" with the list of profiles and the two buttons]

If the app cannot find Afterburner by itself, it says "We couldn't find MSI Afterburner automatically." Click the button and pick the folder yourself.

You only do this once. The app remembers your choice.

# Step 2: Make your first backup

1. On the home screen, click "Back Up My Profiles".
2. Next to "Backup folder:", click "Choose Folder…".
3. Pick where to keep your backups. Good choices are a folder on another drive, like D:\Backups\Afterburner, or a folder on your NAS, like \\NAS\share\AfterburnerBackups.
4. Wait for the message "Backup folder saved."
5. Click "Start Backup".
6. When it finishes, you will see a green message that starts with "Done". It says how many profiles were backed up and that they were checked.
7. Click "Open Backup Folder" to see your backup in File Explorer.

[SCREENSHOT: Backup screen with the backup folder chosen and the Start Backup button]

[SCREENSHOT: Backup screen showing the green Done message and the list of copied profiles]

Each backup goes into its own new folder named with the date and time. Old backups are never replaced.

# Step 3: Try a test run (recommended)

A test run shows what would happen, but copies nothing. It is a safe way to look around.

1. On the home screen, tick "Test run (don't change anything)".
2. Click "Back Up My Profiles", then "Start Backup".
3. The app lists what it would copy and says "Nothing was changed."
4. When you are done, go back and untick the box. The test run switch always starts off when you open the app.

[SCREENSHOT: Home screen with the "Test run (don't change anything)" box ticked]

You can also use a test run before a restore. See Step 4.

# Step 4: Restore your profiles

Do this when you want to put profiles from an earlier backup back into Afterburner.

1. On the home screen, click "Restore Profiles".
2. Windows asks for permission. The app first shows "Administrator permission needed". Click "Continue", then click Yes in the Windows window.
3. The app restarts and opens the restore screen.

[SCREENSHOT: The "Administrator permission needed" message with the Continue and Cancel buttons]

Now you are on "Restore Profiles — Step 1 of 2: Pick a backup".

4. Click the backup you want. The newest one is at the top.
5. If your backups are somewhere else, click "Choose a Different Folder…" first.
6. Click "Next".

[SCREENSHOT: Step 1 of 2 with the list of backups and the Next button]

Now you are on "Restore Profiles — Step 2 of 2: Choose profiles".

7. All profiles are ticked. Click "Select None" and then tick only the ones you want, or leave them all ticked. "Select All" ticks everything again.
8. Click "Restore Selected Profiles".

[SCREENSHOT: Step 2 of 2 with the ticked profiles and the Restore Selected Profiles button]

9. If Afterburner is open, the app says "Afterburner is still open". Click "Close Afterburner for me". If you prefer, click "I'll close it myself", close Afterburner, and click Restore again.
10. The app shows what it will do. Read it, then click "Yes, restore". Click "Cancel" if you are not sure.
11. When it finishes, you will see "Restore finished". Open MSI Afterburner again.

[SCREENSHOT: The "Restore these profiles?" message listing the profiles]

[SCREENSHOT: The "Restore finished" message]

Your old profiles are not lost. The safety copy is in a folder called before-restore, inside your backup folder.

# Practice a restore with a test run

Test a restore once before you need it.

1. Tick "Test run (don't change anything)" on the home screen.
2. Do Step 4. At the end, the button says "Show me" instead of "Yes, restore".
3. The app shows what it would replace. Nothing is changed.

# Good to know

- Profiles with long names that start with VEN are made for one graphics card. They only work on the same graphics card in the same slot.
- If Afterburner is set to apply settings when Windows starts, a restored profile may be applied the next time you start your PC.
- The app never sends anything over the internet.
- Need more help? Click "Help" on the home screen, or see the FAQ and Troubleshooting guides.
