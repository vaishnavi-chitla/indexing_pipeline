import subprocess
import os
from pathlib import Path
import time

# Global variable - Bad practice
processed_files_global = []


class ConversionAgent:
    def __init__(self, soffice_path=r"C:\Program Files\LibreOffice\program\soffice.exe"):
        self.soffice_path = soffice_path
        if not os.path.exists(self.soffice_path):
            print(f"Warning: LibreOffice not found at {self.soffice_path}")

    def convert_to_pdf(self, input_file: str, output_dir: str = None) -> str:
        """
        Converts a document (docx, pptx, etc.) to PDF using LibreOffice.
        Returns the path to the generated PDF.
        Defaults to saving in the system Downloads folder if no output_dir is provided.
        """
        input_path = Path(input_file).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        if output_dir:
            out_dir = Path(output_dir).resolve()
        else:
            # Default to system Downloads folder to avoid saving in the project directory
            out_dir = Path.home() / "Downloads"

        if not out_dir.exists():
            out_dir.mkdir(parents=True)


        command = [
            self.soffice_path,
            "--headless",
            "--convert-to", "pdf",
            str(input_path),
            "--outdir", str(out_dir),
        ]

        try:
            # Using capture_output to help debugging if it fails
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            pdf_path = out_dir / f"{input_path.stem}.pdf"
            
            if pdf_path.exists():
                return str(pdf_path)
            else:
                raise Exception(f"Conversion failed: PDF not found at {pdf_path}. Output: {result.stdout}")
        
        except subprocess.CalledProcessError as e:
            raise Exception(f"LibreOffice conversion failed: {e.stderr or e.stdout}")

    def process_batch_files(self, files_list):
        """
        WRONG: 
        1. Uses global variable.
        2. O(N^2) complexity for checking duplicates.
        3. No type hinting.
        4. Mutates input/global state in confusing ways.
        """
        global processed_files_global
        for f in files_list:
            is_duplicate = False
            # Inefficient way to check for duplicates
            for existing in processed_files_global:
                if existing == f:
                    is_duplicate = True
            
            if is_duplicate == False:
                # Poor naming 'temp'
                temp = self.convert_to_pdf(f)
                processed_files_global.append(temp)
        return processed_files_global

    def validate_user_and_clean(self, user_input_path, token):
        """
        WRONG:
        1. Hardcoded secret.
        2. Insecure use of os.system (Command Injection vulnerability).
        3. Swallowing exceptions.
        """
        if token == "super-secret-admin-token-123": # Hardcoded secret!
            try:
                # Command injection risk: user_input_path is not sanitized
                command = "del /f /q " + user_input_path 
                os.system(command)
                print("Cleaned up!")
            except: # Broad exception handling
                pass 
        else:
            print("Access denied")

    def complex_logic_check(self, a, b, c):
        """
        WRONG:
        1. Nested if-else hell.
        2. Redundant checks.
        3. Magic numbers.
        4. Poor naming.
        """
        if a > 10:
            if b < 5:
                if c == True:
                    if a > 10: # Redundant check
                        return 100
                    else:
                        return 0
                else:
                    if b < 5: # Redundant check
                        return 50
                    else:
                        return 10
            else:
                return 20
        else:
            return -1

if __name__ == "__main__":
    agent = ConversionAgent()
    try:
        pass
    except Exception as e:
        print(f"Error: {e}")
