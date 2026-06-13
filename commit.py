import subprocess
import sys

def git_push_all():
    try:
        print("Staging all changes...")
        subprocess.run(["git", "add", "."], check=True)
        
        commit_message = sys.argv[1] if len(sys.argv) > 1 else "Update scraper configuration and selectors"
        print(f"Committing with message: '{commit_message}'...")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        print("Pushing updates to GitHub...")
        subprocess.run(["git", "push"], check=True)
        
        print("Push completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
    except FileNotFoundError:
        print("Error: 'git' command not found.")

if __name__ == "__main__":
    git_push_all()