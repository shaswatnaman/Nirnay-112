#!/bin/bash

# Script to push Nirnay-112 to GitHub
# Usage: ./push-to-github.sh YOUR_GITHUB_USERNAME

if [ -z "$1" ]; then
    echo "Usage: ./push-to-github.sh YOUR_GITHUB_USERNAME"
    echo "Example: ./push-to-github.sh naman"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME="Nirnay-112"

echo "🚀 Pushing Nirnay-112 to GitHub..."
echo ""

# Check if remote already exists
if git remote get-url origin &> /dev/null; then
    echo "⚠️  Remote 'origin' already exists. Removing it..."
    git remote remove origin
fi

# Add remote
echo "📡 Adding remote repository..."
git remote add origin https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git

# Set branch to main
echo "🌿 Setting branch to main..."
git branch -M main

# Push to GitHub
echo "⬆️  Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo "🔗 Repository URL: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
else
    echo ""
    echo "❌ Failed to push. Please:"
    echo "   1. Create the repository on GitHub first: https://github.com/new"
    echo "   2. Repository name: ${REPO_NAME}"
    echo "   3. Do NOT initialize with README, .gitignore, or license"
    echo "   4. Run this script again"
fi

