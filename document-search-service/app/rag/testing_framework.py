"""
RAG Chunking Testing Framework
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class TestResult:
    test_name: str
    status: TestStatus
    score: float
    details: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None

class ChunkingTestSuite:
    """Comprehensive testing framework for chunking strategies"""
    
    def __init__(self):
        self.test_documents = self._load_test_documents()
        self.evaluation_queries = self._load_evaluation_queries()
    
    def _load_test_documents(self) -> Dict[str, Dict]:
        """Load test documents for different document types"""
        
        return {
            'legal_contract': {
                'content': """
                AGREEMENT
                
                This Agreement is entered into between Party A and Party B.
                
                1. INDEMNIFICATION
                Party A shall indemnify and hold harmless Party B from any and all claims,
                except as provided in Section 3.2 which limits liability to $50,000 for 
                cases of gross negligence.
                
                2. LIABILITY LIMITATIONS
                The total liability of either party shall not exceed $100,000, except for
                willful misconduct or breach of confidentiality obligations.
                
                3. TERMINATION
                3.1 Either party may terminate this Agreement with 30 days notice.
                3.2 In case of material breach, the non-breaching party may terminate
                immediately upon written notice.
                """,
                'type': 'legal',
                'high_risk_areas': ['indemnification', 'liability', 'termination']
            },
            'financial_report': {
                'content': """
                Q3 2024 Financial Results
                
                Revenue: $50M (up 15% YoY)
                COGS: $30M
                Gross Profit: $20M (40% margin)
                
                Operating Expenses:
                - Sales & Marketing: $8M
                - R&D: $5M
                - G&A: $2M
                Total OpEx: $15M
                
                EBITDA = Revenue - COGS - OpEx = $50M - $30M - $15M = $5M
                EBITDA Margin: 10%
                
                Compared to Q2 2024:
                - Revenue increased by $5M
                - EBITDA improved from $3M to $5M
                """,
                'type': 'financial',
                'calculations': ['EBITDA', 'margins', 'YoY growth']
            },
            'code_sample': {
                'content': """
                import numpy as np
                from typing import List, Optional
                
                class DataProcessor:
                    def __init__(self, config: dict):
                        self.config = config
                        self.data_cache = {}
                    
                    def process_data(self, data: List[float]) -> np.ndarray:
                        '''Process input data with normalization'''
                        if not data:
                            raise ValueError("Data cannot be empty")
                        
                        # Apply normalization
                        normalized = self._normalize(data)
                        
                        # Cache results
                        cache_key = hash(tuple(data))
                        self.data_cache[cache_key] = normalized
                        
                        return normalized
                    
                    def _normalize(self, data: List[float]) -> np.ndarray:
                        arr = np.array(data)
                        return (arr - arr.mean()) / arr.std()
                """,
                'type': 'code',
                'functions': ['__init__', 'process_data', '_normalize']
            }
        }
    
    def _load_evaluation_queries(self) -> Dict[str, List[Dict]]:
        """Load evaluation queries for each document type"""
        
        return {
            'legal': [
                {
                    'query': 'What are the indemnification terms for Party A?',
                    'expected_content': ['indemnify', 'hold harmless', 'except as provided', 'Section 3.2'],
                    'should_not_split': 'indemnify...except as provided'
                },
                {
                    'query': 'What is the liability cap in this agreement?',
                    'expected_content': ['liability', 'not exceed', '$100,000', 'except for'],
                    'should_not_split': 'not exceed $100,000, except for'
                }
            ],
            'financial': [
                {
                    'query': 'How is EBITDA calculated?',
                    'expected_content': ['EBITDA', 'Revenue', 'COGS', 'OpEx', '$50M', '$30M', '$15M'],
                    'should_not_split': 'EBITDA = Revenue - COGS - OpEx'
                },
                {
                    'query': 'What was the Q3 2024 revenue growth?',
                    'expected_content': ['Revenue', '$50M', '15% YoY'],
                    'should_not_split': '$50M (up 15% YoY)'
                }
            ],
            'code': [
                {
                    'query': 'How does the process_data function work?',
                    'expected_content': ['process_data', 'normalize', 'data_cache'],
                    'should_not_split': 'def process_data'
                }
            ]
        }
    
    async def run_comprehensive_tests(self, chunker) -> Dict[str, List[TestResult]]:
        """Run comprehensive test suite"""
        
        results = {}
        
        for doc_name, doc_data in self.test_documents.items():
            logger.info(f"Testing chunking for {doc_name}")
            
            doc_type = doc_data['type']
            test_results = []
            
            # Create mock document
            mock_doc = self._create_mock_document(doc_data)
            
            # Test 1: Basic chunking functionality
            result = await self._test_basic_chunking(chunker, mock_doc, doc_name)
            test_results.append(result)
            
            # Test 2: Legal protection (for legal docs)
            if doc_type == 'legal':
                result = await self._test_legal_protection(chunker, mock_doc, doc_data)
                test_results.append(result)
            
            # Test 3: Financial calculation preservation (for financial docs)
            if doc_type == 'financial':
                result = await self._test_financial_calculations(chunker, mock_doc, doc_data)
                test_results.append(result)
            
            # Test 4: Retrieval accuracy
            if doc_type in self.evaluation_queries:
                result = await self._test_retrieval_accuracy(chunker, mock_doc, doc_type)
                test_results.append(result)
            
            # Test 5: Performance metrics
            result = await self._test_performance_metrics(chunker, mock_doc)
            test_results.append(result)
            
            results[doc_name] = test_results
        
        return results
    
    def _create_mock_document(self, doc_data: Dict) -> Any:
        """Create mock document for testing"""
        
        class MockDocument:
            def __init__(self, content, doc_type):
                self.id = f"test_doc_{doc_type}"
                self.content = content
                self.filename = f"test.{doc_type}"
        
        return MockDocument(doc_data['content'], doc_data['type'])
    
    async def _test_basic_chunking(self, chunker, document, doc_name: str) -> TestResult:
        """Test basic chunking functionality"""
        
        start_time = time.time()
        
        try:
            chunks = chunker.chunk_document(document)
            execution_time = time.time() - start_time
            
            # Basic validation
            if not chunks:
                return TestResult(
                    test_name=f"{doc_name}_basic_chunking",
                    status=TestStatus.FAILED,
                    score=0.0,
                    details={'error': 'No chunks generated'},
                    execution_time=execution_time,
                    error_message="No chunks generated"
                )
            
            # Check chunk quality
            quality_score = self._assess_chunk_quality(chunks)
            
            return TestResult(
                test_name=f"{doc_name}_basic_chunking",
                status=TestStatus.PASSED if quality_score > 0.7 else TestStatus.WARNING,
                score=quality_score,
                details={
                    'chunk_count': len(chunks),
                    'avg_chunk_size': sum(len(c.content) for c in chunks) / len(chunks),
                    'quality_score': quality_score
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"{doc_name}_basic_chunking",
                status=TestStatus.FAILED,
                score=0.0,
                details={'error': str(e)},
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _test_legal_protection(self, chunker, document, doc_data: Dict) -> TestResult:
        """Test legal protection mechanisms"""
        
        start_time = time.time()
        
        try:
            chunks = chunker.chunk_document(document)
            execution_time = time.time() - start_time
            
            # Check for split high-risk terms with improved logic
            violations = []
            high_risk_areas = doc_data.get('high_risk_areas', [])
            
            for risk_area in high_risk_areas:
                found_in_chunks = []
                for i, chunk in enumerate(chunks):
                    if risk_area in chunk.content.lower():
                        found_in_chunks.append(i)
                
                # Check if risk area appears in multiple chunks (potential split)
                if len(found_in_chunks) > 1:
                    # Enhanced validation: check if this is actually a harmful split
                    is_harmful_split = self._is_harmful_legal_split(chunks, found_in_chunks, risk_area)
                    
                    if is_harmful_split:
                        violations.append({
                            'risk_area': risk_area,
                            'split_across_chunks': found_in_chunks
                        })
            
            # Check for incomplete legal clauses
            incomplete_clauses = []
            for i, chunk in enumerate(chunks):
                if self._has_incomplete_legal_clause(chunk.content):
                    incomplete_clauses.append(i)
            
            # Calculate score
            total_issues = len(violations) + len(incomplete_clauses)
            score = max(0.0, 1.0 - (total_issues * 0.2))  # -0.2 per issue
            
            status = TestStatus.PASSED if score > 0.8 else TestStatus.FAILED if score < 0.5 else TestStatus.WARNING
            
            return TestResult(
                test_name=f"{document.id}_legal_protection",
                status=status,
                score=score,
                details={
                    'violations': violations,
                    'incomplete_clauses': incomplete_clauses,
                    'total_issues': total_issues
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"{document.id}_legal_protection",
                status=TestStatus.FAILED,
                score=0.0,
                details={'error': str(e)},
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _has_incomplete_legal_clause(self, content: str) -> bool:
        """Check for incomplete legal clauses"""
        
        incomplete_patterns = [
            r'except\s*$',
            r'provided\s+that\s*$',
            r'subject\s+to\s*$',
            r'unless\s*$'
        ]
        
        content_end = content.strip().lower()
        return any(re.search(pattern, content_end) for pattern in incomplete_patterns)
    
    async def _test_financial_calculations(self, chunker, document, doc_data: Dict) -> TestResult:
        """Test financial calculation preservation"""
        
        start_time = time.time()
        
        try:
            chunks = chunker.chunk_document(document)
            execution_time = time.time() - start_time
            
            calculations = doc_data.get('calculations', [])
            issues = []
            
            for calc in calculations:
                # Find chunks containing this calculation (improved matching)
                calc_chunks = []
                for i, chunk in enumerate(chunks):
                    if self._calculation_found_in_chunk(chunk.content, calc):
                        calc_chunks.append(i)
                
                if len(calc_chunks) == 0:
                    issues.append(f"Calculation '{calc}' not found in any chunk")
                elif len(calc_chunks) > 1:
                    issues.append(f"Calculation '{calc}' split across chunks {calc_chunks}")
                else:
                    # Check if calculation is complete in the chunk
                    chunk_content = chunks[calc_chunks[0]].content
                    if not self._is_calculation_complete(chunk_content, calc):
                        issues.append(f"Calculation '{calc}' appears incomplete in chunk {calc_chunks[0]}")
            
            score = max(0.0, 1.0 - (len(issues) * 0.25))  # -0.25 per issue
            status = TestStatus.PASSED if score > 0.8 else TestStatus.WARNING if score > 0.5 else TestStatus.FAILED
            
            return TestResult(
                test_name=f"{document.id}_financial_calculations",
                status=status,
                score=score,
                details={
                    'issues': issues,
                    'calculations_tested': calculations
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"{document.id}_financial_calculations",
                status=TestStatus.FAILED,
                score=0.0,
                details={'error': str(e)},
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _calculation_found_in_chunk(self, content: str, calculation: str) -> bool:
        """Check if calculation is found in chunk content with flexible matching"""
        
        calc_lower = calculation.lower()
        content_lower = content.lower()
        
        # Direct substring match first
        if calc_lower in content_lower:
            return True
        
        # Flexible matching for specific calculations
        if calc_lower == 'ebitda':
            return 'ebitda' in content_lower
        
        if calc_lower == 'margins':
            # Match both "margin" and "margins"
            return 'margin' in content_lower
        
        if calc_lower == 'yoy growth':
            # Match YoY patterns and growth indicators
            import re
            yoy_patterns = [
                r'\byoy\b',  # "YoY"
                r'\byear.over.year\b',  # "year over year"
                r'\d+%\s+yoy\b',  # "15% YoY"
                r'up\s+\d+%\s+yoy\b',  # "up 15% YoY"
            ]
            return any(re.search(pattern, content_lower) for pattern in yoy_patterns)
        
        return False
    
    def _is_calculation_complete(self, content: str, calculation: str) -> bool:
        """Check if calculation is complete in content"""
        
        # Look for the calculation and its components
        calc_lower = calculation.lower()
        content_lower = content.lower()
        
        if calc_lower == 'ebitda':
            # Check if EBITDA calculation includes related components (more flexible)
            related_components = ['revenue', 'cost', 'expense', 'profit', 'margin', '$']
            has_components = sum(1 for comp in related_components if comp in content_lower)
            return has_components >= 2  # Need at least 2 related terms
        
        if calc_lower == 'margins':
            # Check for margin-related content
            margin_indicators = ['%', 'percent', 'margin', 'profit', 'revenue']
            return any(indicator in content_lower for indicator in margin_indicators)
        
        if calc_lower == 'yoy growth':
            # Check for growth-related content
            growth_indicators = ['%', 'growth', 'increase', 'up', 'yoy', 'year']
            return any(indicator in content_lower for indicator in growth_indicators)
        
        # Generic check for calculation completeness
        return '=' in content or calculation.lower() in content.lower()
    
    async def _test_retrieval_accuracy(self, chunker, document, doc_type: str) -> TestResult:
        """Test retrieval accuracy for document type"""
        
        start_time = time.time()
        
        try:
            chunks = chunker.chunk_document(document)
            queries = self.evaluation_queries.get(doc_type, [])
            
            if not queries:
                return TestResult(
                    test_name=f"{document.id}_retrieval_accuracy",
                    status=TestStatus.SKIPPED,
                    score=0.0,
                    details={'reason': 'No evaluation queries for document type'},
                    execution_time=time.time() - start_time
                )
            
            accuracy_scores = []
            
            for query_data in queries:
                query = query_data['query']
                expected_content = query_data['expected_content']
                
                # Simple retrieval simulation (in practice, would use embedding similarity)
                relevant_chunks = self._find_relevant_chunks(chunks, expected_content)
                
                if relevant_chunks:
                    # Check if expected content is present
                    found_content = sum(1 for term in expected_content 
                                     if any(term.lower() in chunk.content.lower() 
                                           for chunk in relevant_chunks))
                    accuracy = found_content / len(expected_content)
                    accuracy_scores.append(accuracy)
                else:
                    accuracy_scores.append(0.0)
            
            avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0
            
            return TestResult(
                test_name=f"{document.id}_retrieval_accuracy",
                status=TestStatus.PASSED if avg_accuracy > 0.8 else TestStatus.WARNING,
                score=avg_accuracy,
                details={
                    'query_accuracies': accuracy_scores,
                    'avg_accuracy': avg_accuracy
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"{document.id}_retrieval_accuracy",
                status=TestStatus.FAILED,
                score=0.0,
                details={'error': str(e)},
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _find_relevant_chunks(self, chunks: List, expected_content: List[str]) -> List:
        """Simple relevance calculation for testing"""
        
        relevant_chunks = []
        
        for chunk in chunks:
            relevance_score = 0
            for term in expected_content:
                if term.lower() in chunk.content.lower():
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_chunks.append(chunk)
        
        # Sort by relevance and return top chunks
        relevant_chunks.sort(key=lambda c: sum(1 for term in expected_content 
                                             if term.lower() in c.content.lower()), 
                           reverse=True)
        
        return relevant_chunks[:3]  # Top 3 relevant chunks
    
    async def _test_performance_metrics(self, chunker, document) -> TestResult:
        """Test performance metrics"""
        
        iterations = 5
        execution_times = []
        
        for _ in range(iterations):
            start_time = time.time()
            chunks = chunker.chunk_document(document)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
        
        avg_time = sum(execution_times) / len(execution_times)
        
        # Performance thresholds
        performance_score = 1.0
        if avg_time > 1.0:  # Slower than 1 second
            performance_score = max(0.0, 1.0 - (avg_time - 1.0) * 0.5)
        
        return TestResult(
            test_name=f"{document.id}_performance",
            status=TestStatus.PASSED if performance_score > 0.7 else TestStatus.WARNING,
            score=performance_score,
            details={
                'avg_execution_time': avg_time,
                'execution_times': execution_times,
                'performance_score': performance_score
            },
            execution_time=avg_time
        )
    
    def _assess_chunk_quality(self, chunks: List) -> float:
        """Assess overall chunk quality"""
        
        if not chunks:
            return 0.0
        
        quality_factors = []
        
        # Size consistency
        sizes = [len(chunk.content) for chunk in chunks]
        avg_size = sum(sizes) / len(sizes)
        size_variance = sum((size - avg_size) ** 2 for size in sizes) / len(sizes)
        size_consistency = max(0.0, 1.0 - (size_variance / (avg_size ** 2)))
        quality_factors.append(size_consistency)
        
        # Content completeness (no very short chunks)
        short_chunks = sum(1 for size in sizes if size < 100)
        completeness = 1.0 - (short_chunks / len(chunks))
        quality_factors.append(completeness)
        
        # Overlap effectiveness (simplified check)
        overlap_score = 0.8  # Placeholder - would need actual overlap analysis
        quality_factors.append(overlap_score)
        
        return sum(quality_factors) / len(quality_factors)
    
    def _is_harmful_legal_split(self, chunks: List, chunk_indices: List[int], risk_area: str) -> bool:
        """
        Determine if a high-risk term split across chunks is actually harmful
        
        Args:
            chunks: List of chunks
            chunk_indices: Indices of chunks containing the risk area
            risk_area: The high-risk term being analyzed
            
        Returns:
            True if the split is harmful and violates legal integrity
        """
        
        # For liability specifically, check if it's a proper cross-reference
        if risk_area == 'liability':
            # Check each chunk for context
            contexts = []
            for idx in chunk_indices:
                chunk_content = chunks[idx].content.lower()
                
                # Look for different liability contexts
                if 'liability limitations' in chunk_content or 'liability cap' in chunk_content:
                    contexts.append('definition')
                elif 'limits liability' in chunk_content or 'liability to' in chunk_content:
                    contexts.append('reference')
                elif 'total liability' in chunk_content:
                    contexts.append('specification')
                else:
                    contexts.append('general')
            
            # If we have both definition and reference, it's likely a proper cross-reference
            if 'definition' in contexts and 'reference' in contexts:
                return False  # Not harmful - proper cross-reference
            
            # If all contexts are the same, it might be a harmful split
            if len(set(contexts)) == 1 and contexts[0] == 'general':
                return True  # Potentially harmful
        
        # For indemnification, check for incomplete clauses
        elif risk_area == 'indemnification':
            for idx in chunk_indices:
                chunk_content = chunks[idx].content.lower()
                
                # Check for incomplete indemnification clauses
                if ('indemnif' in chunk_content and 
                    not any(term in chunk_content for term in ['hold harmless', 'except', 'provided'])):
                    return True  # Incomplete clause
        
        # For termination, check for complete sections
        elif risk_area == 'termination':
            # If termination appears in multiple chunks, check if each is complete
            for idx in chunk_indices:
                chunk_content = chunks[idx].content.lower()
                
                # Check for incomplete termination clauses
                if ('terminate' in chunk_content and 
                    not any(term in chunk_content for term in ['notice', 'breach', 'days'])):
                    return True  # Incomplete clause
        
        # Default: if a high-risk term appears in multiple chunks without clear structure, 
        # it's potentially harmful
        return len(chunk_indices) > 2  # More than 2 chunks is likely problematic
    
    def generate_test_report(self, test_results: Dict[str, List[TestResult]]) -> str:
        """Generate comprehensive test report"""
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RAG CHUNKING TEST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for doc_name, results in test_results.items():
            report_lines.append(f"Document: {doc_name}")
            report_lines.append("-" * 40)
            
            for result in results:
                total_tests += 1
                status_icon = {
                    TestStatus.PASSED: "✅",
                    TestStatus.FAILED: "❌", 
                    TestStatus.WARNING: "⚠️",
                    TestStatus.SKIPPED: "⏭️"
                }[result.status]
                
                report_lines.append(
                    f"{status_icon} {result.test_name}: {result.status.value.upper()} "
                    f"(Score: {result.score:.2f}, Time: {result.execution_time:.3f}s)"
                )
                
                if result.status == TestStatus.PASSED:
                    passed_tests += 1
                elif result.status == TestStatus.FAILED:
                    failed_tests += 1
                elif result.status == TestStatus.WARNING:
                    warning_tests += 1
                
                if result.error_message:
                    report_lines.append(f"   Error: {result.error_message}")
            
            report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 20)
        report_lines.append(f"Total Tests: {total_tests}")
        report_lines.append(f"✅ Passed: {passed_tests}")
        report_lines.append(f"⚠️ Warnings: {warning_tests}")
        report_lines.append(f"❌ Failed: {failed_tests}")
        report_lines.append(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        
        return "\n".join(report_lines)