
import pandas as pd
import os

file_path = r"d:\xireneg_HIDEOUT\GitHub\amazon-ppc\sample_negative_keyword_update_upload.xlsx"

try:
    df = pd.read_excel(file_path)
    print("Columns found in sample file:")
    for col in df.columns:
        print(f"'{col}'")
except Exception as e:
    print(f"Error reading file: {e}")
