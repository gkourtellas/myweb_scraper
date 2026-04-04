import os
import shutil

# Paths
main_file = 'tginfo.txt'
test_file = 'tginfo_test.txt'
backup_file = 'tginfo.txt.bak'

# Backup the original and replace with test
if os.path.exists(main_file):
    shutil.copy2(main_file, backup_file)
    print(f"Backed up {main_file} to {backup_file}")

if os.path.exists(test_file):
    shutil.copy2(test_file, main_file)
    print(f"Copied {test_file} to {main_file}")
else:
    print(f"{test_file} not found!")