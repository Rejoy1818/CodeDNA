"""Generate sample training data for the AI-vs-human code classifier.

Creates balanced examples of human-written and AI-generated code snippets
that can be used to train the classifier via the /api/classify/train endpoint.
"""

import json
import os
import random

HUMAN_SAMPLES = [
    """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
""",
    """
# Read file and count lines
with open('data.txt', 'r') as f:
    lines = f.readlines()
    print(f"Total lines: {len(lines)}")
""",
    """
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def greet(self):
        return f"Hello, {self.name}!"
""",
    """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""",
    """
import requests

def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None
""",
    """
# TODO: refactor this later
items = [1, 2, 3, 4, 5]
result = []
for item in items:
    if item % 2 == 0:
        result.append(item * 2)
""",
    """
def process_data(data):
    # Handle empty input
    if not data:
        return []
    return [x.strip().lower() for x in data if x]
""",
    """
try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows
except Exception as e:
    logger.error(f"Database error: {e}")
    raise
""",
]

AI_GENERATED_SAMPLES = [
    """
def calculate_fibonacci(n: int) -> int:
    \"\"\"Calculate the nth Fibonacci number using recursion.\"\"\"
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
""",
    """
# Read the contents of a file and return the total number of lines
with open('data.txt', mode='r', encoding='utf-8') as file_handle:
    lines = file_handle.readlines()
    total_lines = len(lines)
    print(f"Total lines in file: {total_lines}")
""",
    """
class User:
    \"\"\"A class representing a user with name and email attributes.\"\"\"

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def greet(self) -> str:
        \"\"\"Return a personalized greeting message.\"\"\"
        return f"Hello, {self.name}!"
""",
    """
def bubble_sort(arr: list) -> list:
    \"\"\"Sort a list using the bubble sort algorithm.\"\"\"
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""",
    """
import requests
from typing import Optional, Dict, Any

def fetch_data(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    \"\"\"Fetch JSON data from a URL with error handling.\"\"\"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Error fetching data: {exc}")
        return None
""",
    """
# Process a list of items, filtering even numbers and doubling them
items = [1, 2, 3, 4, 5]
result = [item * 2 for item in items if item % 2 == 0]
""",
    """
def process_data(data: list[str]) -> list[str]:
    \"\"\"Clean and normalise a list of strings.\"\"\"
    if not data:
        return []
    return [item.strip().lower() for item in data if item.strip()]
""",
    """
import sqlite3
import logging

logger = logging.getLogger(__name__)

def fetch_all_users() -> list:
    \"\"\"Retrieve all user records from the database.\"\"\"
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as exc:
        logger.error("Database error occurred: %s", exc)
        raise
    finally:
        conn.close()
""",
]

def generate(num_per_class: int = 50) -> list:
    """Generate balanced training samples.

    Args:
        num_per_class: Number of samples per class.

    Returns:
        List of (code, label) tuples where label 1 = AI-generated, 0 = human.
    """
    samples = []

    # Human samples (label 0)
    for _ in range(num_per_class):
        base = random.choice(HUMAN_SAMPLES)
        # Add slight variation
        samples.append((base, 0))

    # AI-generated samples (label 1)
    for _ in range(num_per_class):
        base = random.choice(AI_GENERATED_SAMPLES)
        samples.append((base, 1))

    random.shuffle(samples)
    return samples


if __name__ == "__main__":
    data = generate(num_per_class=50)
    output_path = os.path.join(os.path.dirname(__file__), "sample_training_data.json")

    json_data = {
        "samples": [item[0] for item in data],
        "labels": [item[1] for item in data],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    print(f"Generated {len(data)} samples -> {output_path}")
    print(f"Human: {sum(1 for _, l in data if l == 0)}, AI: {sum(1 for _, l in data if l == 1)}")