# Nexus Control Center launchd

Plist path:

`~/Library/LaunchAgents/ai.nexus.control-center.plist`

Load:

```bash
cp /Users/raymonddavis/nexus-ai/launchd/ai.nexus.control-center.plist ~/Library/LaunchAgents/ai.nexus.control-center.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.nexus.control-center.plist
launchctl kickstart -k gui/$(id -u)/ai.nexus.control-center
```

Unload:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.nexus.control-center.plist
```

Restart:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.nexus.control-center.plist || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.nexus.control-center.plist
launchctl kickstart -k gui/$(id -u)/ai.nexus.control-center
```

Status:

```bash
launchctl list | grep ai.nexus.control-center
launchctl print gui/$(id -u)/ai.nexus.control-center | sed -n '1,120p'
```

Tail logs:

```bash
tail -f /Users/raymonddavis/nexus-ai/logs/control-center.out.log
tail -f /Users/raymonddavis/nexus-ai/logs/control-center.err.log
```

Rollback:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.nexus.control-center.plist || true
rm -f ~/Library/LaunchAgents/ai.nexus.control-center.plist
```
