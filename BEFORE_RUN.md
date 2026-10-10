# Before run

What your computer needs to open Super Limpio on Windows and on Linux, and how to get anything that is missing.

*Versión en español: [ANTES_DE_EJECUTAR.md](ANTES_DE_EJECUTAR.md)*

## At a glance

| | Windows | Linux |
|---|---|---|
| System | Windows 10 or 11, 64-bit | A distribution with a graphical desktop |
| What to download | `SuperLimpio-<version>-protegido.zip` | `SuperLimpio-<version>-linux.tar.gz` |
| Anything to install | No. The zip includes everything | Python 3.11 or newer, with tkinter |
| Disk space | About 80 MB | Less than 5 MB |
| Internet | Only for the download | Only for the download |
| Administrator rights | No | No |

Both files are on the [Releases](https://github.com/Vex62/Super-Limpio/releases) page. Each system has its own entry: download the one that shows the name of your system.

Super Limpio is not installed. It is a folder: you extract it, open it, and delete it when you no longer want it.

The application is available in English and Spanish. It starts in the language of your system, and you can change it at the bottom of the side bar.

---

## Windows

### What you need

- **Windows 10 or Windows 11, 64-bit.** Almost every computer from the last ten years qualifies. To check: *Settings › System › About*, and look at "System type".
- **About 80 MB of free space** on the disk where you will put the folder. It can be the internal disk, an external disk or a USB drive.
- **Nothing else.** You do not need to install Python or any other program: the zip includes everything the application uses.

### Before you open it

1. **Unblock the zip.** Windows marks files that come from the Internet. Right-click the zip, choose **Properties**, tick **Unblock** (at the bottom) and press **OK**. If you do not see that box, you can skip this step.
2. **Extract the whole zip.** Right-click the zip and choose **Extract All…**. Do not open the program from inside the zip: it will not work.
3. **Keep the folder together.** `SuperLimpio.exe` needs the `app` and `runtime` folders next to it. You can move or copy the complete folder, but do not take the `.exe` out of it. If you want it close at hand, create a shortcut.

Then double-click `SuperLimpio.exe`.

### Messages Windows may show

They are normal and do not mean something is wrong.

| Message | Why it appears | What to do |
|---|---|---|
| "Windows protected your PC" (blue window) | The program is new and does not carry a paid publisher signature | Press **More info** and then **Run anyway**. If you unblocked the zip, it usually does not appear |
| "Do you want to allow this app to make changes?" | Only appears if you ask for an action that needs administrator rights, for example cleaning system folders | Check that the path is your Super Limpio folder and accept. If you say no, nothing is done |
| The antivirus blocks a deletion in Documents or Pictures | "Controlled folder access" is turned on | In *Windows Security › Ransomware protection*, allow `SuperLimpio.exe` |

### Tips

- **Choose a simple folder.** For example `C:\SuperLimpio` or a folder inside your user folder. Avoid very long paths.
- **On a company computer** you may not be allowed to run downloaded programs. In that case, ask the person who manages the computer.
- **If your antivirus flags a file**, do not simply exclude it: check that the download is the original one (see "Check the download" below).
- **You do not need to open it "as administrator".** It works as a standard user and asks for permission only when a specific action requires it.

---

## Linux

### What you need

- **A graphical desktop** (GNOME, KDE, Xfce, Cinnamon, MATE…). Super Limpio is an application with windows; it does not work on a server without a screen.
- **Python 3.11 or newer.**
- **tkinter**, the part of Python that draws the windows. On many distributions it comes in a separate package.

### Check what you have

Open a terminal and type:

```
python3 --version
python3 -c "import tkinter; print('tkinter available')"
```

- If the first line shows `Python 3.11` or a higher number, and the second one answers `tkinter available`, you can already run Super Limpio.
- If not, install what is missing with the command for your distribution.

### Install what is missing

| Distribution | Command |
|---|---|
| Ubuntu 24.04 or newer, Debian 12 or newer, Linux Mint 22 | `sudo apt install python3 python3-tk` |
| Fedora | `sudo dnf install python3 python3-tkinter` |
| Arch Linux, Manjaro | `sudo pacman -S python tk` |
| openSUSE | `sudo zypper install python3 python3-tk` |

These commands ask for your password because they install system packages. Super Limpio itself does not need administrator rights.

**If your distribution ships a Python older than 3.11** (this is the case for Ubuntu 22.04 and Linux Mint 21, which ship 3.10), you have two options:

- Upgrade to a newer release of the distribution. This is the simplest option in the long term.
- Install a newer Python next to the system one, without replacing it. On Ubuntu and its derivatives you can do this with the "deadsnakes" repository:

  ```
  sudo add-apt-repository ppa:deadsnakes/ppa
  sudo apt update
  sudo apt install python3.11 python3.11-tk
  ```

  Nothing else is needed: the Super Limpio launcher looks for `python3.11`, `python3.12`, and so on, and uses the first one that works.

### Before you open it

```
tar -xzf SuperLimpio-<version>-linux.tar.gz
cd SuperLimpio
./superlimpio.sh
```

To add it to the applications menu of your user: `./superlimpio.sh --instalar` (remove it with `--quitar`).

If Python or tkinter is missing, the launcher says so and shows which package to install.

### Optional

- **`wmctrl`**: lets the "Optimize" section know which programs have an open window. Install it with your package manager (`sudo apt install wmctrl`, `sudo dnf install wmctrl`…).
- **A terminal emulator**: "System tools" and program removal open a terminal so that you can see the command and type your password. Every desktop includes one.

### Tips

- **Extract it in your home folder** (for example `~/SuperLimpio`). USB drives formatted as FAT or exFAT do not keep the permission to run files; if it does not start there, use `sh superlimpio.sh`.
- **"Permission denied" when you run it**: restore the permission with `chmod +x superlimpio.sh`.
- **Do not run it with `sudo`.** The application is designed for your own user. Anything that needs privileges opens in a terminal, in plain view, and asks for your password there.
- **Tested on** Ubuntu 22.04 and 24.04. It should work on Fedora, Arch and openSUSE, but it has been tested less there.

---

## Check the download (optional, recommended)

The page of each release shows the **SHA-256** of the file: a fingerprint that only matches if the file is exactly the published one.

- **Windows** (in PowerShell): `Get-FileHash SuperLimpio-<version>-protegido.zip`
- **Linux**: `sha256sum SuperLimpio-<version>-linux.tar.gz`

Compare the result with the one on the page. If it does not match, download the file again and do not open it.

In addition, Super Limpio checks its own integrity every time it starts: if someone has changed or added files in the folder, it refuses to open and says so.

## What to expect when you use it

- **It works offline.** It does not send data anywhere.
- **Nothing is deleted or closed without your confirmation.** Every action first shows what it is going to touch.
- **By default it uses the Recycle Bin / Trash**, from where items can be recovered. Permanent deletion is a separate action.
- **It does not change your system when it opens**: it does not install services, does not stay in the background and does not start by itself.

## If something does not work

| What you see | What to do |
|---|---|
| Windows: "Falta la carpeta app" or "Falta el Python portable" (the `app` folder or the portable Python is missing) | Extract the whole zip and open the `.exe` from the `SuperLimpio` folder, without moving it |
| Windows: nothing happens when you double-click | Check that the antivirus has not removed files from the folder, and extract the zip again |
| Linux: "Super Limpio necesita Python 3.11 o posterior" (it needs Python 3.11 or newer) | Follow "Install what is missing" above |
| Linux: "Falta tkinter" (tkinter is missing) | Install the tkinter package for your distribution (table above) |
| "This copy of Super Limpio has been modified" | The folder is not the original one. Delete it and download again from the Releases page |
| "Super Limpio is already open" | There is already a window open in your session. Only one is allowed at a time |

Still not working? Open an issue at <https://github.com/Vex62/Super-Limpio/issues> and include your system, its version and the exact message you see.
