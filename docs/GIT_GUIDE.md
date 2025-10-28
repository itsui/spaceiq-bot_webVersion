# Git Quick Reference Guide

Your project is now using Git for version control! This guide covers everything you need.

## What Just Happened?

✅ Git repository initialized
✅ Sensitive files protected (`.gitignore` configured)
✅ Initial commit created with all working code

**Your first snapshot is saved!** You can now make changes safely.

---

## Daily Workflow - The Essentials

### 1. Check Status (What changed?)
```bash
git status
```
Shows which files you modified, added, or deleted.

### 2. Save Changes (Create a checkpoint)
```bash
# Add all changed files
git add .

# OR add specific files
git add src/pages/spaceiq_booking_page.py

# Create the snapshot with a message
git commit -m "Fixed date picker bug"
```

### 3. View History (See your checkpoints)
```bash
# Show recent commits
git log --oneline

# Show last 5 commits with details
git log -5
```

---

## Common Scenarios

### Scenario 1: "I want to save my working version before trying something risky"
```bash
# Check what changed
git status

# Save everything
git add .
git commit -m "Working version before experimenting with API changes"
```

### Scenario 2: "I broke something! Go back to the last working version"
```bash
# Undo ALL changes since last commit (CAREFUL!)
git reset --hard HEAD

# OR undo changes to just one file
git checkout -- src/pages/spaceiq_booking_page.py
```

### Scenario 3: "Show me what I changed"
```bash
# See changes in all files
git diff

# See changes in specific file
git diff src/pages/spaceiq_booking_page.py
```

### Scenario 4: "I want to go back to a specific checkpoint"
```bash
# Show history with commit IDs
git log --oneline

# Go back to specific commit (replace abc1234 with actual commit ID)
git checkout abc1234

# To return to the latest version
git checkout master
```

---

## Creating Backup Points

### Before Major Changes
```bash
# Good commit message examples:
git commit -m "Working booking bot - all tests passing"
git commit -m "Added automated session warmer"
git commit -m "Fixed GMT timezone bug"

# Bad examples (too vague):
git commit -m "updates"
git commit -m "fix"
```

### Daily Practice
End each coding session with a commit:
```bash
git add .
git commit -m "End of day - booking bot working, added quick_book.py"
```

---

## Cloud Backup (Recommended!)

Git on your computer protects against coding mistakes, but not hardware failure.
**Solution:** Push to GitHub (free cloud backup)

### One-Time Setup

1. **Create GitHub account** (if you don't have one):
   - Go to https://github.com/join
   - Sign up (free)

2. **Create a new repository** on GitHub:
   - Click "+" → "New repository"
   - Name: `spaceiq-bot` (or whatever you prefer)
   - Make it **PRIVATE** (important for security!)
   - Don't initialize with README (we already have code)
   - Click "Create repository"

3. **Connect your local repo to GitHub**:
```bash
# Replace YOUR-USERNAME with your GitHub username
git remote add origin https://github.com/YOUR-USERNAME/spaceiq-bot.git

# Push your code to GitHub
git push -u origin master
```

### Daily Backup to Cloud
After making commits locally, push to GitHub:
```bash
git push
```

That's it! Your code is now backed up in the cloud.

---

## Emergency Recovery

### "I deleted everything by accident!"
If you've been committing regularly:
```bash
# Go back to last commit
git reset --hard HEAD
```

### "My hard drive failed!"
If you pushed to GitHub:
1. Get a new computer
2. Install Git
3. Clone your repository:
```bash
git clone https://github.com/YOUR-USERNAME/spaceiq-bot.git
```

All your code is recovered!

---

## Advanced: Branching (Experiment Safely)

Create a separate workspace to try new features:

```bash
# Create and switch to experimental branch
git checkout -b experimental-feature

# Make changes, test them...
git add .
git commit -m "Testing new feature"

# If it works, merge back to main code:
git checkout master
git merge experimental-feature

# If it doesn't work, just delete the branch:
git branch -d experimental-feature
```

---

## Quick Reference Card

| Command | What it does |
|---------|-------------|
| `git status` | Show what changed |
| `git add .` | Stage all changes |
| `git commit -m "message"` | Save checkpoint |
| `git log --oneline` | Show history |
| `git diff` | Show changes |
| `git reset --hard HEAD` | Undo all changes |
| `git push` | Backup to cloud |
| `git pull` | Download from cloud |

---

## Tips for Success

1. **Commit often** - Daily or after each feature
2. **Write clear messages** - "Fixed bug" is better than "changes"
3. **Push to GitHub** - Protect against hardware failure
4. **Never commit sensitive data** - `.gitignore` already protects:
   - `playwright/.auth/` (session files)
   - `.env` (passwords)
   - `screenshots/` (potentially sensitive)
   - `logs/` (may contain data)

---

## Current Status

Your repository is ready! You have:
- ✅ 54 files tracked
- ✅ Initial commit created
- ✅ `.gitignore` protecting sensitive data
- ⏳ No cloud backup yet (optional but recommended)

**Next Steps:**
1. Make some changes
2. Run `git add .` and `git commit -m "description"`
3. (Optional) Set up GitHub for cloud backup

---

## Getting Help

```bash
# Get help for any command
git help <command>

# Example:
git help commit
```

**Remember:** Git is like a time machine for your code. Use it liberally!
