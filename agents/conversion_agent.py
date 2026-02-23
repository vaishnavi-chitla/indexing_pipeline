import subprocess
import os
from pathlib import Path

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

if __name__ == "__main__":
    # Test with a file if available
    agent = ConversionAgent()
    try:
        # Example test (commented out to avoid errors if file doesn't exist)
        # result = agent.convert_to_pdf("example.pptx")
        # print(f"Successfully converted: {result}")
        pass
    except Exception as e:
        print(f"Error: {e}")
