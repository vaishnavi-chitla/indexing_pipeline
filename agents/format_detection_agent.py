import os

class FormatDetectionAgent:
    def __init__(self):
        self.conversion_rules = {
            '.pdf': {"original_type": "pdf", "needs_conversion": False},
            '.pptx': {"original_type": "pptx", "needs_conversion": True},
            '.ppt': {"original_type": "ppt", "needs_conversion": True},
            '.docx': {"original_type": "docx", "needs_conversion": True},
            '.doc': {"original_type": "doc", "needs_conversion": True},
        }

    def detect_format(self, file_path: str) -> dict:
        """ Detects the file type and decides if conversion is needed based on the rules: """
        _, ext = os.path.splitext(file_path.lower())
        
        rule = self.conversion_rules.get(ext)
        if rule:
            return rule
        
        return {
            "original_type": ext.lstrip('.') if ext else "unknown",
            "needs_conversion": False
        }

if __name__ == "__main__":
    agent = FormatDetectionAgent()
    
