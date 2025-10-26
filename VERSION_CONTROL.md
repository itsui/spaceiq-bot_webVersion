# Version Control Strategy

## 🔒 Stable Version Locked: v1.0-stable

Your working version has been tagged and saved! You can now experiment safely.

---

## 📌 Current Setup

### Branches:
- **`master`** - Stable production code (always working)
- **`development`** - Experimental features (you are here now ✓)

### Tags:
- **`v1.0-stable`** - Locked working version from 2025-10-26

**Current Branch:** `development` (safe to experiment!)

---

## 🚀 Workflow for New Features

### 1. You're Already on Development Branch
```bash
# Verify you're on development
git branch
# Should show: * development
```

### 2. Make Changes and Commit
```bash
# Make your changes to code...

# Save changes
git add .
git commit -m "Experimenting with new feature X"

# Backup to cloud
git push
```

### 3. If Feature Works - Merge to Master
```bash
# Switch to master
git checkout master

# Merge development into master
git merge development

# Push stable version
git push

# Switch back to development for next feature
git checkout development
```

### 4. If Feature Breaks - Just Delete and Start Over
```bash
# Throw away ALL changes since last commit
git reset --hard HEAD

# OR go back to exact stable version
git reset --hard v1.0-stable
```

---

## 🆘 Emergency Recovery

### Scenario 1: "Everything is broken! Go back to working version!"

**Option A: Reset development branch to stable**
```bash
git checkout development
git reset --hard v1.0-stable
git push --force
```

**Option B: Delete development and recreate from stable**
```bash
git checkout master
git branch -D development
git checkout -b development
git push -u origin development --force
```

**Option C: Use the tag directly**
```bash
git checkout v1.0-stable
# This puts you in "detached HEAD" state - read-only mode
# Look around, test, then:
git checkout development  # Go back to development
```

---

## 📦 Viewing Stable Version

### On GitHub:
1. Visit: https://github.com/itsui/spaceiq-bot
2. Click "Tags" (next to "Branches")
3. Click "v1.0-stable"
4. You'll see the exact locked version

### Locally:
```bash
# List all tags
git tag

# Show tag details
git show v1.0-stable

# Download code at that exact version (read-only)
git checkout v1.0-stable
```

---

## 🔄 Recommended Workflow

### Daily Experimentation:
```bash
# You're on development branch
git add .
git commit -m "Testing new API approach"
git push
```

### When Something Works:
```bash
# Merge to master
git checkout master
git merge development
git push

# Tag new stable version (optional)
git tag -a v1.1-stable -m "Added feature X"
git push origin v1.1-stable

# Back to development
git checkout development
```

### When Something Breaks:
```bash
# Stay on development, just undo
git reset --hard HEAD~1   # Undo last commit
# OR
git reset --hard v1.0-stable  # Go all the way back to stable
```

---

## 📊 Branch Status

### Check Where You Are:
```bash
# Show current branch
git branch

# Show all branches (local and remote)
git branch -a

# Show commit differences
git log master..development --oneline
```

### Switch Between Branches:
```bash
# Go to stable master
git checkout master

# Go to experimental development
git checkout development
```

---

## 🎯 Quick Reference

| What You Want | Command |
|---------------|---------|
| Check current branch | `git branch` |
| Switch to development | `git checkout development` |
| Switch to stable master | `git checkout master` |
| See stable version | `git checkout v1.0-stable` |
| Undo last commit | `git reset --hard HEAD~1` |
| Go back to stable | `git reset --hard v1.0-stable` |
| Merge dev to master | `git checkout master && git merge development` |
| View all tags | `git tag` |

---

## 🛡️ Safety Features

✅ **v1.0-stable tag** - Permanent bookmark to working version
✅ **Development branch** - Safe experimentation space
✅ **Master branch** - Always kept stable
✅ **GitHub backup** - All versions saved in cloud

**You can now experiment fearlessly!** The stable version is locked and can always be restored.

---

## 💡 Pro Tips

1. **Commit often on development** - Each commit is a save point
2. **Test before merging to master** - Keep master always working
3. **Tag major milestones** - `v1.1-stable`, `v2.0-stable`, etc.
4. **Push daily** - Keep GitHub in sync
5. **Don't fear breaking things** - You can always `git reset --hard v1.0-stable`

---

## 📍 Current Status

- Branch: **development** ← You are here
- Stable: **v1.0-stable** (locked and tagged)
- GitHub: https://github.com/itsui/spaceiq-bot
- Status: **Safe to experiment!**

Start coding! Your stable version is protected. 🚀
