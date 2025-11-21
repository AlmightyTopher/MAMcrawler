import os
from datetime import datetime

class ChangeLogger:
    def __init__(self, log_file="CHANGE_LOG.md"):
        self.log_file = log_file

    def log_change(self, description, files_affected, reason, user_action_required=False):
        """
        Log a change to the change log file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        entry = f"\n## [{timestamp}]\n"
        entry += f"- **Description**: {description}\n"
        entry += f"- **Reason**: {reason}\n"
        entry += f"- **Files Affected**: {', '.join(files_affected)}\n"
        entry += f"- **User Action Required**: {'Yes' if user_action_required else 'No'}\n"
        
        # Read existing content
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# Project Change Log\n\n"
            
        # Insert after header
        header_marker = "# Project Change Log"
        if header_marker in content:
            parts = content.split(header_marker)
            new_content = parts[0] + header_marker + entry + parts[1]
        else:
            new_content = content + entry
            
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"Change logged: {description}")

if __name__ == "__main__":
    logger = ChangeLogger()
    logger.log_change("Test Change", ["test.py"], "Testing logger", False)
