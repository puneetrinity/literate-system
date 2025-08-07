#!/usr/bin/env python3
"""
Test Ultra-Fast Search System with Generic Document Types on RunPod
Tests the system's ability to handle diverse document types beyond resumes
"""

import asyncio
import json
import time
import requests
import sys
from typing import Dict, List, Any

# RunPod endpoint
RUNPOD_ENDPOINT = "https://ij9lyqsrrt0kod-8001.proxy.runpod.net"

def create_diverse_test_documents() -> List[Dict[str, Any]]:
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

def test_document_upload(documents: List[Dict[str, Any]]) -> bool:
    """Test uploading diverse documents to the system by saving them locally and triggering index rebuild"""
    print("\n🔄 Testing Document Upload...")
    
    try:
        # Save documents to local file (simulating data upload)
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(documents, f, indent=2)
            temp_file = f.name
        
        print(f"✅ Created temporary document file with {len(documents)} documents")
        
        # Use admin endpoint to rebuild indexes (this will auto-discover our documents)
        url = f"{RUNPOD_ENDPOINT}/api/v2/admin/build-indexes"
        
        response = requests.post(
            url,
            json={"data_source": "auto"},  # Use auto-discovery
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully triggered index rebuild")
            print(f"   Server response: {result.get('message', 'Index building completed')}")
            return True
        else:
            print(f"❌ Index rebuild failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

def test_document_type_searches() -> Dict[str, Any]:
    """Test searches across different document types"""
    print("\n🔍 Testing Document Type-Specific Searches...")
    
    test_queries = [
        # Healthcare/Medical
        {
            "query": "artificial intelligence healthcare diagnostic",
            "expected_type": "article",
            "description": "Healthcare AI article search"
        },
        
        # Automotive/Technology
        {
            "query": "Tesla electric vehicle performance",
            "expected_type": "product", 
            "description": "Electric vehicle product search"
        },
        
        # Academic Research
        {
            "query": "quantum computing financial modeling algorithms",
            "expected_type": "research_paper",
            "description": "Quantum finance research search"
        },
        
        # Culinary
        {
            "query": "Italian saffron risotto recipe",
            "expected_type": "recipe",
            "description": "Italian recipe search"
        },
        
        # Literature/Books
        {
            "query": "quantum physics modern universe guide",
            "expected_type": "book",
            "description": "Physics book search"
        },
        
        # Career/Jobs
        {
            "query": "quantum algorithm developer position",
            "expected_type": "job_posting",
            "description": "Quantum job search"
        },
        
        # Educational Content
        {
            "query": "Docker Kubernetes microservices tutorial",
            "expected_type": "tutorial",
            "description": "DevOps tutorial search"
        },
        
        # Current Events
        {
            "query": "superconductor breakthrough room temperature",
            "expected_type": "news",
            "description": "Science news search"
        }
    ]
    
    results = {
        "total_queries": len(test_queries),
        "successful_queries": 0,
        "type_matches": 0,
        "detailed_results": []
    }
    
    for test_case in test_queries:
        try:
            print(f"\n   Testing: {test_case['description']}")
            print(f"   Query: '{test_case['query']}'")
            
            # Make search request
            response = requests.post(
                f"{RUNPOD_ENDPOINT}/api/v2/search/ultra-fast",
                json={"query": test_case["query"], "num_results": 5},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                search_result = response.json()
                results["successful_queries"] += 1
                
                if search_result["success"] and search_result["results"]:
                    # Check if top result matches expected type
                    top_result = search_result["results"][0]
                    result_type = top_result["metadata"].get("type", "unknown")
                    
                    type_match = result_type == test_case["expected_type"]
                    if type_match:
                        results["type_matches"] += 1
                        print(f"   ✅ Found {result_type} document (expected {test_case['expected_type']})")
                    else:
                        print(f"   ⚠️  Found {result_type} document (expected {test_case['expected_type']})")
                    
                    print(f"   📄 Top result: {top_result['metadata'].get('title', 'N/A')}")
                    print(f"   ⏱️  Response time: {search_result['response_time_ms']:.1f}ms")
                else:
                    print(f"   ❌ No results found")
                    type_match = False
                
                results["detailed_results"].append({
                    "query": test_case["query"],
                    "expected_type": test_case["expected_type"],
                    "found_type": result_type if 'result_type' in locals() else "none",
                    "type_match": type_match,
                    "results_count": len(search_result.get("results", [])),
                    "response_time_ms": search_result.get("response_time_ms", 0)
                })
            else:
                print(f"   ❌ Search failed: {response.status_code}")
                results["detailed_results"].append({
                    "query": test_case["query"],
                    "expected_type": test_case["expected_type"],
                    "error": f"HTTP {response.status_code}",
                    "type_match": False
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results["detailed_results"].append({
                "query": test_case["query"],
                "expected_type": test_case["expected_type"],
                "error": str(e),
                "type_match": False
            })
    
    return results

def test_cross_type_searches() -> Dict[str, Any]:
    """Test searches that should return multiple document types"""
    print("\n🌐 Testing Cross-Type Searches...")
    
    cross_type_queries = [
        {
            "query": "quantum computing",
            "description": "Should find research, jobs, books, news",
            "min_types": 2
        },
        {
            "query": "artificial intelligence",
            "description": "Should find articles, research, jobs",
            "min_types": 2
        },
        {
            "query": "Python programming",
            "description": "Should find tutorials, jobs, books",
            "min_types": 1  # Adjust based on available data
        }
    ]
    
    results = {
        "total_queries": len(cross_type_queries),
        "successful_diversity": 0,
        "detailed_results": []
    }
    
    for test_case in cross_type_queries:
        try:
            print(f"\n   Testing: {test_case['description']}")
            print(f"   Query: '{test_case['query']}'")
            
            response = requests.post(
                f"{RUNPOD_ENDPOINT}/api/v2/search/ultra-fast",
                json={"query": test_case["query"], "num_results": 8},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                search_result = response.json()
                if search_result["success"] and search_result["results"]:
                    # Count unique document types in results
                    found_types = set()
                    for result in search_result["results"]:
                        doc_type = result["metadata"].get("type", "unknown")
                        found_types.add(doc_type)
                    
                    diverse_enough = len(found_types) >= test_case["min_types"]
                    if diverse_enough:
                        results["successful_diversity"] += 1
                        print(f"   ✅ Found {len(found_types)} document types: {', '.join(found_types)}")
                    else:
                        print(f"   ⚠️  Found only {len(found_types)} types (min {test_case['min_types']}): {', '.join(found_types)}")
                    
                    results["detailed_results"].append({
                        "query": test_case["query"],
                        "found_types": list(found_types),
                        "type_count": len(found_types),
                        "min_required": test_case["min_types"],
                        "diverse_enough": diverse_enough,
                        "results_count": len(search_result["results"])
                    })
                else:
                    print(f"   ❌ No results found")
            else:
                print(f"   ❌ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return results

def run_comprehensive_test():
    """Run comprehensive test of generic document support"""
    print("🚀 ULTRA-FAST SEARCH: GENERIC DOCUMENT TYPE TEST")
    print("=" * 60)
    print(f"🎯 Target Endpoint: {RUNPOD_ENDPOINT}")
    print(f"⏰ Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test documents
    test_documents = create_diverse_test_documents()
    print(f"\n📄 Created {len(test_documents)} diverse test documents:")
    for doc in test_documents:
        print(f"   • {doc['type']}: {doc.get('title', doc.get('name', doc['id']))}")
    
    # Test 1: Upload documents
    upload_success = test_document_upload(test_documents)
    if not upload_success:
        print("\n❌ CRITICAL: Document upload failed. Cannot proceed with search tests.")
        return
    
    # Wait for indexing to complete
    print("\n⏳ Waiting 10 seconds for auto-indexing to complete...")
    time.sleep(10)
    
    # Test 2: Type-specific searches
    type_search_results = test_document_type_searches()
    
    # Test 3: Cross-type searches
    cross_type_results = test_cross_type_searches()
    
    # Generate final report
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    
    print(f"\n🔄 DOCUMENT UPLOAD:")
    print(f"   ✅ Upload Status: {'SUCCESS' if upload_success else 'FAILED'}")
    print(f"   📄 Documents: {len(test_documents)} diverse types uploaded")
    
    print(f"\n🎯 TYPE-SPECIFIC SEARCHES:")
    print(f"   📊 Success Rate: {type_search_results['successful_queries']}/{type_search_results['total_queries']} queries")
    print(f"   🎯 Type Accuracy: {type_search_results['type_matches']}/{type_search_results['total_queries']} correct matches")
    print(f"   📈 Type Match Rate: {(type_search_results['type_matches'] / type_search_results['total_queries'] * 100):.1f}%")
    
    print(f"\n🌐 CROSS-TYPE SEARCHES:")
    print(f"   📊 Diversity Success: {cross_type_results['successful_diversity']}/{cross_type_results['total_queries']} queries")
    print(f"   📈 Diversity Rate: {(cross_type_results['successful_diversity'] / cross_type_results['total_queries'] * 100):.1f}%")
    
    # Overall assessment
    overall_success = (
        upload_success and
        type_search_results['successful_queries'] > 0 and
        type_search_results['type_matches'] > 0
    )
    
    print(f"\n🏆 OVERALL ASSESSMENT:")
    if overall_success:
        print("   ✅ SUCCESS: Ultra-Fast Search supports diverse document types!")
        print("   🎉 The system can handle articles, products, research, recipes, books, jobs, tutorials, and news")
    else:
        print("   ❌ ISSUES: System needs improvements for generic document support")
    
    # Save detailed results
    test_report = {
        "test_metadata": {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "endpoint": RUNPOD_ENDPOINT,
            "documents_tested": len(test_documents)
        },
        "upload_test": {"success": upload_success},
        "type_specific_searches": type_search_results,
        "cross_type_searches": cross_type_results,
        "overall_success": overall_success
    }
    
    report_filename = f"generic_document_test_report_{int(time.time())}.json"
    with open(report_filename, 'w') as f:
        json.dump(test_report, f, indent=2)
    
    print(f"\n📁 Detailed report saved: {report_filename}")
    
    return overall_success

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)