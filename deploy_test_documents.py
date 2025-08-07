#!/usr/bin/env python3
"""
Deploy test documents to RunPod and run generic document tests
"""

import json
from enhanced_document_handler import create_sample_generic_documents

def create_comprehensive_test_documents():
    """Create diverse document types for testing"""
    return [
        # Article
        {
            "id": "article_1",
            "type": "article",
            "title": "The Future of Artificial Intelligence in Healthcare",
            "author": "Dr. Sarah Johnson",
            "content": "Artificial intelligence is revolutionizing healthcare through predictive analytics, diagnostic imaging, and personalized treatment plans. Machine learning algorithms can now detect diseases earlier than human doctors in many cases.",
            "tags": ["AI", "healthcare", "machine learning", "diagnostics"],
            "category": "Technology",
            "publication_year": 2024,
            "word_count": 850
        },
        
        # Product
        {
            "id": "product_1",
            "type": "product", 
            "name": "Tesla Model S Plaid",
            "title": "Tesla Model S Plaid Electric Vehicle",
            "brand": "Tesla",
            "description": "High-performance electric sedan with tri-motor all-wheel drive, 0-60 mph in 1.99 seconds, and 405-mile range. Features autopilot, over-the-air updates, and sustainable luxury.",
            "categories": ["electric vehicles", "cars", "luxury", "performance"],
            "specifications": {
                "acceleration": "0-60 mph in 1.99s",
                "range": "405 miles",
                "top_speed": "200 mph",
                "motors": "tri-motor AWD"
            },
            "price": 129990,
            "rating": 4.7
        },
        
        # Research Paper
        {
            "id": "research_1",
            "type": "research_paper",
            "title": "Quantum Computing Applications in Financial Modeling",
            "authors": ["Dr. Michael Chen", "Dr. Lisa Wang", "Prof. David Rodriguez"],
            "abstract": "This paper explores the application of quantum computing algorithms to complex financial modeling problems. We demonstrate significant speedups in portfolio optimization, risk analysis, and derivative pricing using quantum annealing and variational quantum eigensolvers.",
            "keywords": ["quantum computing", "finance", "portfolio optimization", "risk analysis", "QAOA"],
            "publication_year": 2024,
            "category": "Computer Science",
            "venue": "Nature Quantum Information"
        },
        
        # Recipe
        {
            "id": "recipe_1",
            "type": "recipe",
            "title": "Authentic Italian Risotto Milanese",
            "cuisine": "Italian",
            "description": "Traditional Milanese risotto with saffron, Arborio rice, and Parmigiano-Reggiano. A creamy, luxurious dish that embodies Northern Italian cuisine at its finest.",
            "ingredients": ["Arborio rice", "saffron", "beef broth", "white wine", "onion", "Parmigiano-Reggiano", "butter"],
            "duration": 35,
            "difficulty": "medium",
            "tags": ["Italian", "risotto", "saffron", "comfort food"],
            "servings": 4
        },
        
        # Book
        {
            "id": "book_1",
            "type": "book",
            "title": "The Quantum Universe: A Guide to Modern Physics",
            "author": "Dr. Amanda Foster",
            "description": "An accessible exploration of quantum mechanics, relativity, and modern physics. Explains complex concepts through clear analogies and real-world applications, making advanced physics understandable for general readers.",
            "genres": ["science", "physics", "education", "popular science"],
            "publication_year": 2024,
            "page_count": 420,
            "isbn": "978-0123456789",
            "publisher": "Scientific Press"
        },
        
        # Job Posting
        {
            "id": "job_1",
            "type": "job_posting",
            "title": "Senior Quantum Algorithm Developer",
            "company": "QuantumTech Solutions",
            "location": "Boston, MA",
            "description": "Join our quantum computing team to develop cutting-edge algorithms for financial modeling and optimization. Work with quantum hardware, simulators, and hybrid classical-quantum systems.",
            "requirements": ["Python", "Qiskit", "quantum algorithms", "linear algebra", "optimization"],
            "tags": ["quantum computing", "algorithms", "senior level", "research"],
            "salary_range": "$180k-250k",
            "remote_ok": True
        },
        
        # Tutorial
        {
            "id": "tutorial_1",
            "type": "tutorial",
            "title": "Building Microservices with Docker and Kubernetes",
            "difficulty": "intermediate",
            "duration": 120,
            "description": "Comprehensive guide to containerizing applications and orchestrating them with Kubernetes. Covers service discovery, load balancing, scaling, and deployment strategies.",
            "topics": ["Docker", "Kubernetes", "microservices", "containerization", "DevOps"],
            "tools": ["Docker Desktop", "kubectl", "VS Code"],
            "author": "DevOps Academy"
        },
        
        # News Article
        {
            "id": "news_1",
            "type": "news",
            "headline": "Breakthrough in Room-Temperature Superconductor Research",
            "title": "Scientists Achieve Room-Temperature Superconductivity",
            "content": "Researchers at Stanford University have developed a new material that exhibits superconducting properties at room temperature and ambient pressure. This breakthrough could revolutionize energy transmission, magnetic levitation, and quantum computing.",
            "topics": ["superconductors", "physics", "energy", "research", "Stanford"],
            "author": "Science Correspondent",
            "publication_year": 2024,
            "category": "Science"
        }
    ]

if __name__ == "__main__":
    # Create comprehensive test documents
    test_documents = create_comprehensive_test_documents()
    
    # Save to a file that the system can discover
    with open('generic_test_documents.json', 'w') as f:
        json.dump(test_documents, f, indent=2)
    
    print(f"✅ Created {len(test_documents)} diverse test documents:")
    for doc in test_documents:
        print(f"   • {doc['type']}: {doc.get('title', doc.get('name', doc['id']))}")
    
    print("\n📁 Saved to: generic_test_documents.json")
    print("🚀 Ready for deployment to RunPod!")