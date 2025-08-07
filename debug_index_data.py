#!/usr/bin/env python3
"""
Debug Ultra-Fast Search Index Data
Compare what's actually in the indexes vs expected data
"""

import pickle
import numpy as np
import os

def analyze_index_data(index_path, label):
    print(f"\n🔍 ANALYZING {label} INDEX DATA")
    print("=" * 50)
    
    other_data_path = os.path.join(index_path, "other_data.pkl")
    
    if not os.path.exists(other_data_path):
        print(f"❌ No other_data.pkl found at {other_data_path}")
        return
    
    try:
        with open(other_data_path, "rb") as f:
            data = pickle.load(f)
        
        print(f"📊 Index Contents:")
        print(f"   • Document Vectors: {len(data.get('document_vectors', {}))}")
        print(f"   • Document Metadata: {len(data.get('document_metadata', {}))}")
        print(f"   • BM25 Index: {len(data.get('bm25_index', {}))}")
        print(f"   • Doc Frequencies: {len(data.get('doc_frequencies', {}))}")
        print(f"   • Corpus Size: {data.get('corpus_size', 0)}")
        print(f"   • Avg Doc Length: {data.get('avg_doc_length', 0)}")
        print(f"   • Doc IDs: {len(data.get('doc_ids', []))}")
        
        # Check if document vectors contain actual data
        doc_vectors = data.get('document_vectors', {})
        if doc_vectors:
            if isinstance(doc_vectors, list):
                vectors_array = np.array(doc_vectors)
                print(f"   • Vector Shape: {vectors_array.shape}")
                print(f"   • Vector Data Type: {vectors_array.dtype}")
                print(f"   • Vector Range: {vectors_array.min():.4f} to {vectors_array.max():.4f}")
            else:
                print(f"   • Document Vectors Type: {type(doc_vectors)}")
                if hasattr(doc_vectors, 'keys'):
                    sample_keys = list(doc_vectors.keys())[:3]
                    print(f"   • Sample Doc IDs: {sample_keys}")
                    for key in sample_keys:
                        vec = doc_vectors[key]
                        if hasattr(vec, 'shape'):
                            print(f"     - {key}: shape {vec.shape}, range {vec.min():.4f} to {vec.max():.4f}")
        
        # Check BM25 index
        bm25_index = data.get('bm25_index', {})
        if bm25_index:
            sample_keys = list(bm25_index.keys())[:3]
            print(f"   • Sample BM25 Entries:")
            for key in sample_keys:
                entry = bm25_index[key]
                tf_count = len(entry.get('tf', {}))
                doc_length = entry.get('length', 0)
                print(f"     - {key}: {tf_count} terms, length {doc_length}")
        
        # Check LSH Index
        lsh_index = data.get('lsh_index')
        if lsh_index:
            print(f"   • LSH Index: {type(lsh_index)}")
            if hasattr(lsh_index, '__dict__'):
                print(f"     - LSH attributes: {list(lsh_index.__dict__.keys())}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error reading index data: {str(e)}")
        return None

def main():
    print("🔍 ULTRA-FAST SEARCH INDEX DEBUG")
    print("=" * 60)
    
    # Analyze current system
    current_path = "/home/ews/unified-ai-system-clean/document-search-service/indexes"
    current_data = analyze_index_data(current_path, "CURRENT SYSTEM")
    
    # Analyze ideal-octo-goggles system
    ideal_path = "/home/ews/unified-ai-search-system/ai-chat-service/ideal-octo-goggles/indexes"
    ideal_data = analyze_index_data(ideal_path, "IDEAL-OCTO-GOGGLES")
    
    # Compare data availability
    print(f"\n🔄 COMPARISON SUMMARY")
    print("=" * 30)
    
    if current_data and ideal_data:
        current_docs = len(current_data.get('document_metadata', {}))
        ideal_docs = len(ideal_data.get('document_metadata', {}))
        
        print(f"📊 Document Count:")
        print(f"   • Current System: {current_docs}")
        print(f"   • Ideal System: {ideal_docs}")
        
        if current_docs == 0:
            print(f"\n❗ ROOT CAUSE IDENTIFIED:")
            print(f"   The Ultra-Fast Search engine is returning 0% recall because")
            print(f"   NO DOCUMENTS ARE LOADED INTO THE INDEXES!")
            print(f"   The system is initialized but empty.")
        elif current_docs == ideal_docs:
            print(f"\n✅ Both systems have equal document counts.")
            print(f"   The 0% recall issue is likely in the search logic.")
        else:
            print(f"\n⚠️ Document count mismatch detected.")
            print(f"   Current system may have incomplete data.")
    
    # Check data source files
    print(f"\n📁 DATA SOURCE CHECK")
    print("=" * 30)
    
    data_sources = [
        "/home/ews/unified-ai-system-clean/document-search-service/data/resumes.json",
        "/home/ews/unified-ai-search-system/ai-chat-service/ideal-octo-goggles/data/resumes.json"
    ]
    
    for source in data_sources:
        if os.path.exists(source):
            try:
                import json
                with open(source, 'r') as f:
                    data = json.load(f)
                print(f"✅ {source}: {len(data)} documents")
            except Exception as e:
                print(f"❌ {source}: Error - {str(e)}")
        else:
            print(f"❌ {source}: Not found")

if __name__ == "__main__":
    main()