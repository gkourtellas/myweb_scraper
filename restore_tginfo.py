import os
import shutil

# Paths
main_file = 'tginfo.txt'
backup_file = 'tginfo.txt.bak'

# Restore the backup
if os.path.exists(backup_file):
    shutil.copy2(backup_file, main_file)
    print(f"Restored {main_file} from {backup_file}")
else:
    print(f"No backup file {backup_file} found!")