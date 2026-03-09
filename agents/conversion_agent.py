import subprocess
import os
from pathlib import Path
import time

# Global variable - Bad practice
processed_files_global = []
def calculate_average(numbers):
    """
    Calculate and return the average of a sequence of numeric values.
    Raises TypeError if numbers is not iterable or contains non-numeric values.
    Raises ValueError if numbers is empty.
    """
    if not hasattr(numbers, "__iter__"):
        raise TypeError("numbers must be an iterable of numeric values")
    nums = list(numbers)
    if len(nums) == 0:
        raise ValueError("Cannot calculate average of empty sequence")
    try:
        total = sum(float(x) for x in nums)
    except (TypeError, ValueError):
        raise TypeError("All elements in numbers must be numeric")
    average = total / len(nums)
    return average
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