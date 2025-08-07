#!/usr/bin/env python3
"""
Enhanced Generic Document Handler for Ultra-Fast Search
Supports any document type with flexible field mapping
"""

from typing import Dict, List, Any, Optional
import json

class GenericDocumentHandler:
    """
    Handles any document type by intelligently extracting searchable content
    """
    
    # Field mappings for different document types
    FIELD_MAPPINGS = {
        # Common text fields that should be searchable
        'title_fields': ['title', 'name', 'headline', 'subject', 'topic'],
        'content_fields': ['content', 'description', 'abstract', 'summary', 'body', 'text'],
        'author_fields': ['author', 'authors', 'creator', 'writer'],
        'tag_fields': ['tags', 'keywords', 'categories', 'topics', 'genres'],
        'skill_fields': ['skills', 'technologies', 'tools', 'requirements', 'ingredients'],
        'meta_fields': ['type', 'category', 'genre', 'difficulty', 'cuisine', 'brand']
    }
    
    def extract_searchable_text(self, doc: Dict[str, Any]) -> str:
        """
        Extract all searchable text from any document type
        """
        text_parts = []
        
        # Extract title/name
        for field in self.FIELD_MAPPINGS['title_fields']:
            if field in doc and doc[field]:
                text_parts.append(str(doc[field]))
        
        # Extract main content
        for field in self.FIELD_MAPPINGS['content_fields']:
            if field in doc and doc[field]:
                text_parts.append(str(doc[field]))
        
        # Extract authors
        for field in self.FIELD_MAPPINGS['author_fields']:
            if field in doc and doc[field]:
                if isinstance(doc[field], list):
                    text_parts.extend([str(author) for author in doc[field]])
                else:
                    text_parts.append(str(doc[field]))
        
        # Extract tags and keywords
        for field in self.FIELD_MAPPINGS['tag_fields']:
            if field in doc and doc[field]:
                if isinstance(doc[field], list):
                    text_parts.extend([str(tag) for tag in doc[field]])
                else:
                    text_parts.append(str(doc[field]))
        
        # Extract skills/technologies/tools
        for field in self.FIELD_MAPPINGS['skill_fields']:
            if field in doc and doc[field]:
                if isinstance(doc[field], list):
                    text_parts.extend([str(skill) for skill in doc[field]])
                else:
                    text_parts.append(str(doc[field]))
        
        # Extract metadata
        for field in self.FIELD_MAPPINGS['meta_fields']:
            if field in doc and doc[field]:
                text_parts.append(str(doc[field]))
        
        # Handle nested objects (like specifications)
        for key, value in doc.items():
            if isinstance(value, dict):
                # Extract text from nested objects
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (str, int, float)):
                        text_parts.append(f"{nested_key} {nested_value}")
        
        return ' '.join(text_parts)
    
    def extract_features(self, doc: Dict[str, Any]) -> List[str]:
        """
        Extract features for LSH indexing from any document type
        """
        features = []
        
        # Extract from all skill/tag fields
        for field in self.FIELD_MAPPINGS['skill_fields'] + self.FIELD_MAPPINGS['tag_fields']:
            if field in doc and doc[field]:
                if isinstance(doc[field], list):
                    features.extend([str(item).lower() for item in doc[field]])
                else:
                    features.append(str(doc[field]).lower())
        
        # Extract words from text content
        text = self.extract_searchable_text(doc)
        features.extend(text.lower().split())
        
        return list(set(features))  # Remove duplicates
    
    def get_display_title(self, doc: Dict[str, Any]) -> str:
        """
        Get the best display title for any document type
        """
        for field in self.FIELD_MAPPINGS['title_fields']:
            if field in doc and doc[field]:
                return str(doc[field])
        
        # Fallback to document ID
        return doc.get('id', 'Unknown Document')
    
    def get_document_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata for any document type
        """
        metadata = {}
        
        # Always include document type
        metadata['type'] = doc.get('type', 'unknown')
        metadata['title'] = self.get_display_title(doc)
        
        # Include author information
        for field in self.FIELD_MAPPINGS['author_fields']:
            if field in doc and doc[field]:
                metadata['author'] = doc[field]
                break
        
        # Include relevant numeric/categorical data
        numeric_fields = ['year', 'publication_year', 'price', 'rating', 'page_count', 'word_count', 'duration']
        for field in numeric_fields:
            if field in doc and doc[field] is not None:
                metadata[field] = doc[field]
        
        # Include categorical data
        categorical_fields = ['category', 'genre', 'difficulty', 'cuisine', 'brand', 'location']
        for field in categorical_fields:
            if field in doc and doc[field]:
                metadata[field] = doc[field]
        
        # Include tags/keywords
        for field in self.FIELD_MAPPINGS['tag_fields']:
            if field in doc and doc[field]:
                metadata[field] = doc[field]
                break
        
        return metadata
    
    def validate_document(self, doc: Dict[str, Any]) -> bool:
        """
        Validate that a document has minimum required fields
        """
        # Must have an ID
        if 'id' not in doc or not doc['id']:
            return False
        
        # Must have at least one searchable field
        searchable_text = self.extract_searchable_text(doc)
        if not searchable_text or len(searchable_text.strip()) < 3:
            return False
        
        return True
    
    def convert_legacy_resume(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert legacy resume format to generic document format
        """
        if 'type' not in doc:
            doc['type'] = 'resume'
        
        # Map resume-specific fields to generic fields
        if 'name' in doc and 'title' not in doc:
            doc['title'] = doc['name']
        
        return doc

def create_sample_generic_documents() -> List[Dict[str, Any]]:
    """
    Create sample documents of various types for testing
    """
    return [
        # Article
        {
            "id": "article_1",
            "type": "article",
            "title": "Introduction to Machine Learning",
            "author": "Dr. Sarah Johnson",
            "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. This comprehensive guide covers the fundamentals of supervised learning, unsupervised learning, and reinforcement learning techniques.",
            "tags": ["machine learning", "AI", "data science", "algorithms"],
            "category": "Technology",
            "publication_year": 2024,
            "word_count": 2500
        },
        
        # Product
        {
            "id": "product_1",
            "type": "product", 
            "name": "MacBook Pro 16-inch",
            "title": "MacBook Pro 16-inch M3 Max",
            "brand": "Apple",
            "description": "The most powerful MacBook Pro ever built with M3 Max chip, featuring exceptional performance for demanding workflows. Perfect for developers, designers, and creative professionals.",
            "categories": ["laptops", "computers", "apple", "professional"],
            "specifications": {
                "processor": "Apple M3 Max",
                "memory": "32GB unified memory",
                "storage": "1TB SSD",
                "display": "16-inch Liquid Retina XDR"
            },
            "price": 3499,
            "rating": 4.8
        },
        
        # Research Paper
        {
            "id": "research_1",
            "type": "research_paper",
            "title": "Transformer Networks in Natural Language Processing",
            "authors": ["Michael Chen", "Lisa Wang", "David Rodriguez"],
            "abstract": "This paper presents a comprehensive analysis of transformer architectures in natural language processing tasks. We evaluate performance across multiple benchmarks including GLUE, SuperGLUE, and custom datasets, demonstrating significant improvements in accuracy and efficiency.",
            "keywords": ["transformers", "NLP", "deep learning", "attention mechanisms", "BERT", "GPT"],
            "publication_year": 2024,
            "category": "Computer Science"
        },
        
        # Recipe
        {
            "id": "recipe_1",
            "type": "recipe",
            "title": "Classic Italian Carbonara",
            "cuisine": "Italian",
            "description": "An authentic Roman carbonara recipe using eggs, cheese, pancetta, and black pepper. This traditional pasta dish requires no cream and delivers rich, silky texture through proper technique.",
            "ingredients": ["spaghetti", "eggs", "pecorino romano", "pancetta", "black pepper", "salt"],
            "duration": 20,
            "difficulty": "medium",
            "tags": ["pasta", "Italian", "traditional", "quick"]
        },
        
        # Book
        {
            "id": "book_1",
            "type": "book",
            "title": "The Future of Artificial Intelligence",
            "author": "Dr. Amanda Foster",
            "description": "A thought-provoking exploration of AI's impact on society, covering ethical considerations, technological advances, and future implications for human civilization.",
            "genres": ["technology", "science", "philosophy", "future studies"],
            "publication_year": 2024,
            "page_count": 384
        },
        
        # Job Posting
        {
            "id": "job_1",
            "type": "job_posting",
            "title": "Senior Software Engineer - AI/ML",
            "company": "TechCorp Inc.",
            "location": "San Francisco, CA",
            "description": "Join our cutting-edge AI team to build next-generation machine learning systems. We're looking for an experienced engineer passionate about artificial intelligence and scalable software architecture.",
            "requirements": ["Python", "TensorFlow", "PyTorch", "Docker", "Kubernetes"],
            "tags": ["software engineering", "machine learning", "artificial intelligence", "senior level"]
        },
        
        # Tutorial
        {
            "id": "tutorial_1",
            "type": "tutorial",
            "title": "Getting Started with Docker Containers",
            "difficulty": "beginner",
            "duration": 45,
            "description": "Learn the fundamentals of Docker containerization technology. This hands-on tutorial covers installation, basic commands, creating Dockerfiles, and deploying your first containerized application.",
            "topics": ["docker", "containers", "devops", "development", "deployment"],
            "tools": ["Docker Desktop", "text editor"]
        },
        
        # News Article
        {
            "id": "news_1",
            "type": "news",
            "headline": "Major Breakthrough in Quantum Computing Announced",
            "title": "Major Breakthrough in Quantum Computing Announced",
            "content": "Researchers at MIT have achieved a significant milestone in quantum computing, demonstrating error correction at scale. This advancement brings us closer to practical quantum computers that could revolutionize cryptography, drug discovery, and financial modeling.",
            "topics": ["quantum computing", "MIT", "research", "technology", "breakthrough"],
            "author": "Jennifer Martinez",
            "publication_year": 2024
        }
    ]

def test_generic_document_handler():
    """
    Test the generic document handler with various document types
    """
    handler = GenericDocumentHandler()
    sample_docs = create_sample_generic_documents()
    
    print("🧪 TESTING GENERIC DOCUMENT HANDLER")
    print("=" * 50)
    
    for doc in sample_docs:
        print(f"\n📄 Testing {doc['type']}: {doc.get('title', doc.get('name', 'N/A'))}")
        
        # Test text extraction
        text = handler.extract_searchable_text(doc)
        print(f"   📝 Extracted text: {text[:100]}...")
        
        # Test feature extraction
        features = handler.extract_features(doc)
        print(f"   🏷️  Features: {features[:8]}...")
        
        # Test metadata extraction
        metadata = handler.get_document_metadata(doc)
        print(f"   📋 Metadata: {list(metadata.keys())}")
        
        # Test validation
        is_valid = handler.validate_document(doc)
        print(f"   ✅ Valid: {is_valid}")
    
    print(f"\n🎯 Successfully processed {len(sample_docs)} different document types!")
    
    # Save sample documents
    with open('generic_test_documents.json', 'w') as f:
        json.dump(sample_docs, f, indent=2)
    
    print("📁 Saved test documents to: generic_test_documents.json")

if __name__ == "__main__":
    test_generic_document_handler()