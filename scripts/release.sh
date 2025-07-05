#!/bin/bash
# ArgoCD Release Script
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh v1.17.0

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.17.0"
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must follow semantic versioning format (e.g., v1.17.0)"
    exit 1
fi

echo "🚀 Creating release $VERSION"

# Check if tag already exists
if git tag -l | grep -q "^$VERSION$"; then
    echo "Error: Tag $VERSION already exists"
    exit 1
fi

# Ensure we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Warning: You're not on main branch. Current branch: $CURRENT_BRANCH"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create and push tag
echo "📝 Creating tag $VERSION"
git tag "$VERSION"
git push origin "$VERSION"

# Update all applications to new version
echo "🔄 Updating ArgoCD applications to $VERSION"
find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
    sed -i "s/targetRevision: .*/targetRevision: \"$VERSION\"/" {} \;

# Show what was changed
echo "📋 Updated applications:"
git diff --name-only playbooks/yaml/argocd-apps/

# Commit the updates
echo "💾 Committing application updates"
git add playbooks/yaml/argocd-apps/
git commit -m "chore: update applications to $VERSION"
git push origin main

echo "✅ Released $VERSION successfully!"
echo "🔗 ArgoCD will automatically sync to the new version"