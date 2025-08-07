"""
Enhanced Startup Module for Ultra-Fast Search System
Handles automatic index building and data initialization
"""

import os
import json
import asyncio
from typing import Optional
from pathlib import Path

from app.search.ultra_fast_engine import UltraFastSearchEngine
from app.config import settings
from app.logger import get_enhanced_logger

logger = get_enhanced_logger(__name__)

async def initialize_search_engine_with_auto_indexing() -> UltraFastSearchEngine:
    """
    Initialize search engine and automatically build indexes if needed
    """
    logger.info("Initializing Ultra-Fast Search Engine with auto-indexing...")
    
    # Create search engine
    search_engine = UltraFastSearchEngine(
        embedding_dim=settings.embedding_dim,
        use_gpu=settings.use_gpu
    )
    
    # Check if we need to build indexes
    needs_indexing = await _check_if_indexing_needed(search_engine)
    
    if needs_indexing:
        logger.info("Indexes are missing or empty, attempting to build automatically...")
        
        # Try to find and load data
        documents = await _find_and_load_documents()
        
        if documents:
            logger.info(f"Found {len(documents)} documents, building indexes...")
            await search_engine.build_indexes(documents)
            logger.info("✅ Indexes built successfully during startup")
        else:
            logger.warning("⚠️  No documents found for automatic indexing. Indexes will be empty.")
            logger.info("Use the /admin/build-indexes endpoint to build indexes when data is available.")
    else:
        logger.info("✅ Indexes already exist and appear to be populated")
    
    return search_engine

async def _check_if_indexing_needed(search_engine: UltraFastSearchEngine) -> bool:
    """
    Check if indexes need to be built
    """
    try:
        # Check if index files exist
        index_path = Path(settings.index_path)
        hnsw_index = index_path / "hnsw.index"
        other_data = index_path / "other_data.pkl"
        
        if not hnsw_index.exists() or not other_data.exists():
            logger.info("Index files missing, will build indexes")
            return True
        
        # Check if indexes are empty (minimal size indicates empty indexes)
        if hnsw_index.stat().st_size < 1000 or other_data.stat().st_size < 1000:
            logger.info("Index files appear to be empty or minimal, will rebuild")
            return True
        
        # Try to perform a test search to verify indexes work
        try:
            results = await search_engine.search("test", num_results=1)
            if len(results) == 0:
                logger.info("Search returned no results, indexes may be empty")
                return True
            else:
                logger.info(f"Test search returned {len(results)} results, indexes appear functional")
                return False
        except Exception as e:
            logger.warning(f"Test search failed: {e}, will rebuild indexes")
            return True
            
    except Exception as e:
        logger.error(f"Error checking index status: {e}, assuming indexes need building")
        return True

async def _find_and_load_documents() -> Optional[list]:
    """
    Find and load documents from various possible locations
    """
    # Possible data file locations (in order of preference)
    possible_data_files = [
        Path(settings.data_path) / "resumes.json",
        Path("./data/resumes.json"),
        Path("./data/documents.json"),
        Path("./data/sample_documents.json"),
        Path("../data/resumes.json"),
        Path("./resumes.json"),
    ]
    
    # Also check for directories with JSON files
    possible_data_dirs = [
        Path(settings.data_path) / "documents",
        Path("./data/documents"),
        Path("./data/rag_documents"),
        Path("../data/documents"),
    ]
    
    # Try to load from JSON files first
    for data_file in possible_data_files:
        if data_file.exists():
            try:
                logger.info(f"Found data file: {data_file}")
                with open(data_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                
                if isinstance(documents, list) and len(documents) > 0:
                    # Validate document structure
                    valid_docs = []
                    for doc in documents:
                        if isinstance(doc, dict) and 'id' in doc:
                            valid_docs.append(doc)
                        else:
                            logger.warning(f"Invalid document structure: {doc}")
                    
                    if valid_docs:
                        logger.info(f"Loaded {len(valid_docs)} valid documents from {data_file}")
                        return valid_docs
                
            except Exception as e:
                logger.warning(f"Failed to load data from {data_file}: {e}")
                continue
    
    # Try to load from directories with individual JSON files
    for data_dir in possible_data_dirs:
        if data_dir.exists() and data_dir.is_dir():
            try:
                logger.info(f"Checking directory: {data_dir}")
                json_files = list(data_dir.glob("*.json"))
                
                if json_files:
                    documents = []
                    for json_file in json_files[:100]:  # Increased limit for more documents
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                doc = json.load(f)
                                if isinstance(doc, dict):
                                    # Ensure document has an ID
                                    if 'id' not in doc:
                                        doc['id'] = json_file.stem
                                    
                                    # Convert RAG document format to generic format if needed
                                    if 'chunks' in doc and 'content' in doc:
                                        # This is a RAG document, extract main content
                                        rag_doc = {
                                            'id': doc['id'],
                                            'type': doc.get('metadata', {}).get('type', 'document'),
                                            'title': doc.get('metadata', {}).get('title', f"Document {doc['id']}"),
                                            'content': doc.get('content', ''),
                                            'metadata': doc.get('metadata', {}),
                                            'upload_date': doc.get('upload_date'),
                                            'filename': doc.get('filename', '')
                                        }
                                        documents.append(rag_doc)
                                    else:
                                        # Regular document format
                                        documents.append(doc)
                        except Exception as e:
                            logger.warning(f"Failed to load {json_file}: {e}")
                    
                    if documents:
                        logger.info(f"Loaded {len(documents)} documents from directory {data_dir}")
                        # Continue loading to get MORE documents, don't return yet
                        
            except Exception as e:
                logger.warning(f"Failed to process directory {data_dir}: {e}")
                continue
    
    # Collect all documents from all sources
    all_documents = []
    
    # Try to load from JSON files again and collect them
    for data_file in possible_data_files:
        if data_file.exists():
            try:
                logger.info(f"Loading additional documents from: {data_file}")
                with open(data_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                
                if isinstance(documents, list) and len(documents) > 0:
                    valid_docs = []
                    for doc in documents:
                        if isinstance(doc, dict) and 'id' in doc:
                            valid_docs.append(doc)
                    
                    if valid_docs:
                        all_documents.extend(valid_docs)
                        logger.info(f"Added {len(valid_docs)} documents from {data_file}")
                        
            except Exception as e:
                logger.warning(f"Failed to load additional data from {data_file}: {e}")
    
    # Try to load from directories again and collect them
    for data_dir in possible_data_dirs:
        if data_dir.exists() and data_dir.is_dir():
            try:
                logger.info(f"Loading additional documents from directory: {data_dir}")
                json_files = list(data_dir.glob("*.json"))
                
                if json_files:
                    for json_file in json_files[:100]:
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                doc = json.load(f)
                                if isinstance(doc, dict):
                                    if 'id' not in doc:
                                        doc['id'] = json_file.stem
                                    
                                    # Convert RAG document format if needed
                                    if 'chunks' in doc and 'content' in doc:
                                        rag_doc = {
                                            'id': doc['id'],
                                            'type': doc.get('metadata', {}).get('type', 'document'),
                                            'title': doc.get('metadata', {}).get('title', f"Document {doc['id']}"),
                                            'content': doc.get('content', ''),
                                            'metadata': doc.get('metadata', {}),
                                            'upload_date': doc.get('upload_date'),
                                            'filename': doc.get('filename', '')
                                        }
                                        all_documents.append(rag_doc)
                                    else:
                                        all_documents.append(doc)
                        except Exception as e:
                            logger.warning(f"Failed to load {json_file}: {e}")
                        
            except Exception as e:
                logger.warning(f"Failed to process directory {data_dir}: {e}")
    
    # Remove duplicates based on document ID
    unique_documents = {}
    for doc in all_documents:
        doc_id = doc.get('id')
        if doc_id and doc_id not in unique_documents:
            unique_documents[doc_id] = doc
    
    final_documents = list(unique_documents.values())
    
    if final_documents:
        logger.info(f"Successfully loaded {len(final_documents)} unique documents from all sources")
        return final_documents
    
    # If no data found, create sample data
    logger.warning("No existing data found, creating sample documents for demonstration")
    return _create_sample_documents()

def _create_sample_documents() -> list:
    """
    Create sample documents for demonstration purposes
    """
    sample_docs = [
        {
            "id": "sample_1",
            "name": "John Doe",
            "experience_years": 5,
            "seniority_level": "senior",
            "skills": ["Python", "Machine Learning", "AI", "Deep Learning", "TensorFlow"],
            "technologies": ["TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy"],
            "title": "Senior AI Engineer",
            "description": "Experienced AI engineer with expertise in machine learning, deep learning, and artificial intelligence systems. Specializes in building scalable ML pipelines and neural networks for production environments."
        },
        {
            "id": "sample_2",
            "name": "Jane Smith",
            "experience_years": 3,
            "seniority_level": "mid",
            "skills": ["JavaScript", "React", "Node.js", "Python", "TypeScript"],
            "technologies": ["React", "Express", "MongoDB", "Docker", "Kubernetes"],
            "title": "Full Stack Developer",
            "description": "Full stack developer specializing in modern web technologies. Experience building responsive React applications and scalable Node.js backend services with microservices architecture."
        },
        {
            "id": "sample_3",
            "name": "Alice Johnson",
            "experience_years": 8,
            "seniority_level": "senior",
            "skills": ["Data Science", "Python", "SQL", "Machine Learning", "Statistics"],
            "technologies": ["Pandas", "NumPy", "PostgreSQL", "Apache Spark", "Jupyter"],
            "title": "Senior Data Scientist",
            "description": "Senior data scientist with extensive experience in analytics, statistical modeling, and big data processing. Expert in Python, SQL, and distributed computing systems for large-scale data analysis."
        },
        {
            "id": "sample_4",
            "name": "Bob Wilson",
            "experience_years": 6,
            "seniority_level": "senior",
            "skills": ["DevOps", "Kubernetes", "Docker", "Python", "Terraform"],
            "technologies": ["AWS", "Docker", "Kubernetes", "Terraform", "Jenkins"],
            "title": "DevOps Engineer",
            "description": "DevOps engineer focused on cloud infrastructure automation and container orchestration. Experience with AWS, Kubernetes, and infrastructure as code using Terraform."
        },
        {
            "id": "sample_5",
            "name": "Carol Davis",
            "experience_years": 4,
            "seniority_level": "mid",
            "skills": ["Java", "Spring Boot", "Microservices", "REST APIs", "Database Design"],
            "technologies": ["Java", "Spring Boot", "PostgreSQL", "Redis", "Apache Kafka"],
            "title": "Backend Developer",
            "description": "Backend developer specializing in Java and Spring Boot microservices. Experience designing and implementing scalable REST APIs and distributed systems with event-driven architecture."
        }
    ]
    
    # Save sample documents to data directory
    try:
        data_dir = Path(settings.data_path)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        sample_file = data_dir / "sample_documents.json"
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_docs, f, indent=2)
        
        logger.info(f"Created sample documents file: {sample_file}")
    except Exception as e:
        logger.warning(f"Failed to save sample documents: {e}")
    
    return sample_docs

async def verify_search_functionality(search_engine: UltraFastSearchEngine) -> bool:
    """
    Verify that the search engine is working properly
    """
    try:
        test_queries = ["python", "machine learning", "developer", "senior"]
        
        for query in test_queries:
            results = await search_engine.search(query, num_results=3)
            if len(results) > 0:
                logger.info(f"✅ Search verification passed: '{query}' returned {len(results)} results")
                
                # Log a sample result for debugging
                sample_result = results[0]
                logger.info(f"Sample result: {sample_result.doc_id} - {sample_result.metadata.get('name', 'N/A')}")
                return True
        
        logger.warning("⚠️  Search verification failed: No results returned for any test query")
        return False
        
    except Exception as e:
        logger.error(f"❌ Search verification failed with error: {e}")
        return False