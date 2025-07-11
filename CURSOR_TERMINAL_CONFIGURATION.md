# Cursor Terminal Configuration & Hanging Issue Resolution

## Issue Summary
**Problem**: Random terminal command hanging requiring manual intervention (pressing Enter)  
**Root Cause**: Parallel `run_terminal_cmd` tool execution causes deadlocks  
**Solution**: Use sequential terminal commands only + optimized Cursor settings

## Configuration Files

### 1. Cursor Settings: `/home/drj/.config/Cursor/User/settings.json`
Critical settings that prevent hanging:
```json
{
  "terminal.integrated.automationProfile.linux": {
    "path": "/bin/bash",
    "args": ["--noprofile", "--norc"],
    "env": {
      "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin",
      "PS1": "\\w $ ",
      "PAGER": "cat",
      "GIT_PAGER": "cat",
      "DEBIAN_FRONTEND": "noninteractive",
      "HISTFILE": "/dev/null"
    }
  },
  "terminal.integrated.shellIntegration.enabled": false,
  "git.autofetch": false
}
```

### 2. Bashrc: `/home/drj/.bashrc`
Ultra-minimal configuration for automation:
```bash
#!/bin/bash
# Ultra-minimal bashrc for Cursor
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
export PS1='\w $ '
export PAGER=cat
export GIT_PAGER=cat
export HISTFILE=/dev/null
set +H
```

## Enforcement Rules

### ✅ DO:
- Use sequential terminal commands only
- Wait for each command to complete before the next
- Use single commands with complex logic when possible
- Monitor for hanging and report immediately

### ❌ DON'T:
- Never use parallel `run_terminal_cmd` calls
- Avoid shell integration features
- Don't use interactive commands in automation
- Never use commands that wait for user input

## Troubleshooting

### If hanging occurs:
1. Press Enter to break the deadlock
2. Check if parallel terminal commands were used
3. Verify Cursor settings are correct
4. Restart terminal session if needed

### Performance verification:
```bash
# Should complete in <50ms
time git status --porcelain

# Should show 1 bash process
ps aux | grep -E "bash.*pts" | wc -l

# Should show automation environment
env | grep -E "(PAGER|GIT_PAGER|DEBIAN_FRONTEND)"
```

## Status: RESOLVED
- **Date**: 2025-07-11
- **Settings**: Configured and persistent
- **Behavior**: Sequential commands enforced
- **Performance**: Sub-second command execution achieved

## Memory Reference
- Memory ID: 2923680
- Contains critical behavioral guidelines for AI assistants 