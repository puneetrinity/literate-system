#!/usr/bin/env python3
"""
Simple Debug - Check Raw Index Data
"""

import pickle
import os

def check_raw_pickle(filepath):
    try:
        with open(filepath, "rb") as f:
            # Read the raw pickle data without imports
            import pickletools
            f.seek(0)
            print(f"\n📄 {filepath}:")
            print("Raw pickle contents (first few operations):")
            ops = list(pickletools.genops(f))[:20]  # First 20 operations
            for op in ops:
                print(f"  {op}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_file_hex(filepath, bytes_to_read=100):
    try:
        with open(filepath, "rb") as f:
            data = f.read(bytes_to_read)
            print(f"\n📄 {filepath} (first {bytes_to_read} bytes as hex):")
            print(data.hex())
            print(f"As string: {data[:50]}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 SIMPLE INDEX DEBUG")
    print("=" * 40)
    
    files_to_check = [
        "/home/ews/unified-ai-system-clean/document-search-service/indexes/other_data.pkl",
        "/home/ews/unified-ai-search-system/ai-chat-service/ideal-octo-goggles/indexes/other_data.pkl"
    ]
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"\n📊 {filepath}")
            print(f"   Size: {size} bytes")
            check_file_hex(filepath, 200)
        else:
            print(f"❌ {filepath} not found")
            
    # Check if files are identical
    if len(files_to_check) == 2 and all(os.path.exists(f) for f in files_to_check):
        with open(files_to_check[0], "rb") as f1, open(files_to_check[1], "rb") as f2:
            data1 = f1.read()
            data2 = f2.read()
            if data1 == data2:
                print(f"\n✅ FILES ARE IDENTICAL")
            else:
                print(f"\n❌ FILES ARE DIFFERENT")
                print(f"   File 1 size: {len(data1)}")
                print(f"   File 2 size: {len(data2)}")
                # Find first difference
                for i, (b1, b2) in enumerate(zip(data1, data2)):
                    if b1 != b2:
                        print(f"   First difference at byte {i}: {b1:02x} vs {b2:02x}")
                        break

    # Check the actual data files
    print(f"\n📁 CHECKING DATA SOURCE FILES")
    print("=" * 40)
    
    import json
    data_files = [
        "/home/ews/unified-ai-system-clean/document-search-service/data/resumes.json",
        "/home/ews/unified-ai-search-system/ai-chat-service/ideal-octo-goggles/data/resumes.json"
    ]
    
    for data_file in data_files:
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    print(f"\n✅ {data_file}")
                    print(f"   Documents: {len(data)}")
                    if data:
                        first_doc = data[0]
                        print(f"   Sample keys: {list(first_doc.keys())}")
                        print(f"   Sample ID: {first_doc.get('id', 'N/A')}")
            except Exception as e:
                print(f"❌ Error reading {data_file}: {e}")

if __name__ == "__main__":
    main()