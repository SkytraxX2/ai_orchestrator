#!/bin/bash
echo "🔧 Fixing GitHub Authentication"
echo "You need a Personal Access Token!"
echo ""
echo "Quick steps:"
echo "1. Go to: https://github.com/settings/tokens"
echo "2. Click 'Generate new token (classic)'"
echo "3. Check 'repo' box"
echo "4. Copy the token"
echo ""
read -p "Enter your token here: " TOKEN
read -p "Enter your username (Skytraxx2): " USERNAME

# Remove old remote and add new with token
git remote remove origin 2>/dev/null
git remote add origin "https://$USERNAME:$TOKEN@github.com/$USERNAME/ai_orchestrator.git"

echo "✅ Fixed! Now try: git push"
