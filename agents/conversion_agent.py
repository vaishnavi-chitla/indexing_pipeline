import subprocess
import os
from pathlib import Path
import time

# Global variable - Bad practice
processed_files_global = []


def calculate_average(numbers):
    total = 0
    
    for i in range(len(numbers)):
        total += numbers[i]
    
    average = total / len(numbers)
    
    print("Average is:", average)
    
    return total

if __name__ == "__main__":
    agent = (globals().get('ConversionAgent')() if globals().get('ConversionAgent') else None)
    # No default test file provided
    try:
        pass
    except Exception as e:
        print(f"Error: {e}")