import subprocess
import os
from pathlib import Path
import time

# Global variable - Bad practice
processed_files_global = []


def calculate_average(numbers):
    """
    Calculate and return the arithmetic mean of a non-empty iterable of numbers.

    Raises:
        ValueError: if numbers is empty.
    """
    # Convert to list to support arbitrary iterables/generators and to check emptiness
    nums = list(numbers)
    if not nums:
        raise ValueError("calculate_average requires a non-empty iterable of numbers")
    total = sum(nums)
    count = len(nums)
    return total / count
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