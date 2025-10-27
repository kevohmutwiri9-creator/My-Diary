#!/usr/bin/env python3
"""
Security Fix Script - Generate New SECRET_KEY and Clean Git History
"""
import secrets
import os

def generate_secret_key():
    """Generate a new cryptographically secure SECRET_KEY"""
    return secrets.token_hex(32)

def main():
    print("=" * 70)
    print("🔐 SECURITY REMEDIATION SCRIPT")
    print("=" * 70)
    print()
    
    # Generate new SECRET_KEY
    new_secret = generate_secret_key()
    print("✅ Generated new SECRET_KEY:")
    print(f"   {new_secret}")
    print()
    
    # Check if .env exists
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        print("📝 Found existing .env file")
        print()
        print("⚠️  ACTION REQUIRED:")
        print("   1. Open your .env file")
        print(f"   2. Replace SECRET_KEY with: {new_secret}")
        print("   3. Save the file")
        print()
    else:
        print("⚠️  No .env file found!")
        print("   1. Copy .env.example to .env")
        print(f"   2. Set SECRET_KEY={new_secret}")
        print()
    
    print("=" * 70)
    print("🧹 CLEAN GIT HISTORY (REQUIRED)")
    print("=" * 70)
    print()
    print("The old SECRET_KEY is in git history and must be removed.")
    print()
    print("Run these commands:")
    print()
    print("# Install git-filter-repo (if not installed)")
    print("pip install git-filter-repo")
    print()
    print("# Remove .env from git history")
    print("git filter-repo --path .env --invert-paths --force")
    print()
    print("# Force push to GitHub")
    print("git remote add origin https://github.com/kevohmutwiri9-creator/My-Diary.git")
    print("git push origin --force --all")
    print()
    print("=" * 70)
    print("🔒 ADDITIONAL SECURITY STEPS")
    print("=" * 70)
    print()
    print("1. ✅ Update .env with new SECRET_KEY (copy from above)")
    print("2. ✅ Regenerate any exposed API keys:")
    print("   - Gmail App Password (if exposed)")
    print("   - Gemini API Key (if exposed)")
    print("   - Database passwords (if exposed)")
    print()
    print("3. ✅ Update Render environment variables:")
    print("   - Go to https://dashboard.render.com")
    print("   - Select your app")
    print("   - Go to 'Environment'")
    print(f"   - Update SECRET_KEY to: {new_secret}")
    print()
    print("4. ✅ Verify .gitignore includes .env")
    print("5. ✅ Never commit .env file again!")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
