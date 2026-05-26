#!/usr/bin/env bash
# =============================================================================
# Run this ONCE as yourself (sudo required) to make PM2 auto-start on reboot.
# =============================================================================
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "Installing PM2 launchd startup agent (requires sudo)..."
sudo env PATH="$PATH" /Users/raymonddavis/.nvm/versions/node/v22.22.3/lib/node_modules/pm2/bin/pm2 startup launchd -u raymonddavis --hp /Users/raymonddavis

echo ""
echo "Saving current process list to persist on reboot..."
pm2 save

echo ""
echo "Done. PM2 services will auto-start on next login."
echo "Verify with: pm2 list"
