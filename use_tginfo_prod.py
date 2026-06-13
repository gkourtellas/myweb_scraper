import os
import shutil

# Paths
main_file = 'tginfo.txt'
prod_file = 'tginfo_prod.txt'
backup_file = 'tginfo.txt.bak'

def main():
    # Entry point for switching to production tginfo
    pass

if __name__ == "__main__":
    main()

# Backup the original and replace with production
if os.path.exists(main_file):
    shutil.copy2(main_file, backup_file)
    print(f"Backed up {main_file} to {backup_file}")

if os.path.exists(prod_file):
    shutil.copy2(prod_file, main_file)
    print(f"Copied {prod_file} to {main_file}")
else:
    print(f"{prod_file} not found!")

