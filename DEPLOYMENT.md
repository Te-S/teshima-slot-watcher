# EC2 Deployment Guide

## 📋 **What Changed**

The slot watcher now supports a `config.json` file to specify target dates for monitoring.

### New Features:
- ✅ **Selective date monitoring** - Only check specific dates you care about
- ✅ **Configurable behavior** - Switch between "check all dates" and "check specific dates" modes
- ✅ **Backwards compatible** - Works with or without config file

---

## 🚀 **Deployment Steps to EC2**

### **Step 1: SSH into your EC2 instance**

```bash
ssh ec2-user@your-ec2-ip-address
```

### **Step 2: Navigate to project directory**

```bash
cd ~/projects/slot-watcher-app/slot-watcher
```

### **Step 3: Pull the latest code**

```bash
git pull origin main
```

### **Step 4: Create or update your config file**

```bash
vi config.json
```

Press `i` to enter insert mode, then paste:

**Option A: Check ALL dates (current behavior)**
```json
{
  "check_all_dates": true,
  "target_dates": []
}
```

**Option B: Check ONLY specific dates**
```json
{
  "check_all_dates": false,
  "target_dates": [
    "2025-10-22",
    "2025-10-23",
    "2025-10-24",
    "2025-10-29",
    "2025-10-30"
  ]
}
```

Then:
- Press `ESC`
- Type `:wq`
- Press `ENTER`

### **Step 5: Test the new code**

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
source ~/projects/slot-watcher-app/.env

# Run a test
python3 slot_watcher.py

# Check the output - you should see:
# - "Loaded configuration from config.json"
# - "Monitoring specific dates: ['2025-10-22', ...]" (if using target dates)
# - Only notifications for your target dates
```

### **Step 6: Verify it's working**

```bash
# Check the log output
tail -20 ~/projects/slot-watcher-app/cron.log

# Watch it run in real-time
tail -f ~/projects/slot-watcher-app/cron.log
```

**That's it!** The cron job will automatically pick up the new code on the next run (every 5 minutes).

---

## 📝 **Config File Format**

### **config.json**

```json
{
  "check_all_dates": false,
  "target_dates": [
    "2025-10-22",
    "2025-10-23"
  ]
}
```

### **Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `check_all_dates` | boolean | If `true`, monitors all available dates. If `false`, only monitors dates in `target_dates` |
| `target_dates` | array | List of dates to monitor in `YYYY-MM-DD` format |

### **Notes:**
- Dates must be in `YYYY-MM-DD` format
- If no config file exists, defaults to checking all dates
- Config is loaded on each run, so changes take effect immediately
- Invalid dates in the list are logged and skipped

---

## ✅ **Verification**

After deployment, check the logs for:

```
INFO - Loaded configuration from config.json
INFO - Monitoring specific dates: ['2025-10-22', '2025-10-23', ...]
```

If you see these messages, the config is working! 🎉

---

## 🔄 **Updating Target Dates**

To update your target dates later:

1. SSH into EC2
2. Edit the config file: `vi ~/projects/slot-watcher-app/slot-watcher/config.json`
3. Update the `target_dates` array
4. Save and exit
5. Changes take effect on next run (no restart needed!)

---

## 🐛 **Troubleshooting**

### Config file not loading?
```bash
# Check if config file exists
ls -la ~/projects/slot-watcher-app/slot-watcher/config.json

# Check file permissions
cat ~/projects/slot-watcher-app/slot-watcher/config.json
```

### Still checking all dates?
Make sure `"check_all_dates": false` in your config file.

### Dates not being monitored?
Check the log for "Invalid date format" warnings - ensure dates are in `YYYY-MM-DD` format.


