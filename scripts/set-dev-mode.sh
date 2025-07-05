#!/bin/bash
# ArgoCD Development Mode Script
# Sets all applications to use HEAD for development

set -e

echo "🔧 Setting ArgoCD applications to development mode (HEAD)"

# Update all applications to use HEAD
find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
    sed -i 's/targetRevision: .*/targetRevision: "HEAD"/' {} \;

# Show what was changed
echo "📋 Updated applications:"
git diff --name-only playbooks/yaml/argocd-apps/

# Show current status
echo "📊 Current targetRevision values:"
grep -r "targetRevision:" playbooks/yaml/argocd-apps/ | sort

# Commit the updates
if [ "$(git diff --name-only playbooks/yaml/argocd-apps/)" ]; then
    echo "💾 Committing development mode updates"
    git add playbooks/yaml/argocd-apps/
    git commit -m "chore: set applications to development mode (HEAD)"
    
    echo "✅ Applications updated to development mode!"
    echo "🔗 ArgoCD will now track the HEAD of your branch"
else
    echo "✅ All applications already in development mode"
fi