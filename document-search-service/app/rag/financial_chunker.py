"""
Financial Document Chunking with Calculation Preservation
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FinancialElement:
    element_type: str  # 'calculation', 'table', 'metric', 'period'
    content: str
    dependencies: List[str]
    position: Tuple[int, int]

class FinancialDocumentChunker:
    """Specialized chunker for financial documents"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Enhanced financial patterns
        self.calculation_patterns = [
            r'=\s*[\d\w\s+\-*/()]+',  # Excel-style formulas
            r'\btotal\s*=\s*[\d,]+',
            r'\b\w+\s*=\s*\w+\s*[+\-*/]\s*\w+',
            r'sum\s*\([^)]+\)',
            r'average\s*\([^)]+\)',
            r'ebitda\s*=\s*[^=]+',  # EBITDA calculation
            r'\$[\d,]+\.?\d*\s*[+\-*/]\s*\$[\d,]+\.?\d*',  # Currency calculations
            r'\b\w+\s*[+\-*/]\s*\w+\s*=\s*\$?[\d,]+\.?\d*',  # Basic arithmetic
            r'(?i)\b(revenue|profit|ebitda|cogs|opex)\s*[=:]?\s*\$?[\d,]+\.?\d*[kmb]?\s*[+\-*/]\s*\$?[\d,]+\.?\d*[kmb]?\s*=\s*\$?[\d,]+\.?\d*[kmb]?',  # Complex financial calculations
            r'(?i)\b(margin|percentage|%)\s*[=:]?\s*[\d,]+\.?\d*%?',  # Margin calculations
            r'(?i)\b(up|down|increase|decrease)\s+[\d,]+\.?\d*%?\s+(yoy|year.over.year)',  # Growth patterns
        ]
        
        self.metric_patterns = [
            r'\b(revenue|profit|loss|ebitda|roi|margin)\s*:?\s*\$?[\d,]+\.?\d*[kmb]?\b',
            r'\b(q[1-4]|quarter|quarterly)\s+\d{4}\b',
            r'\b(fy|fiscal\s+year)\s*\d{2,4}\b'
        ]
        
        self.table_indicators = [
            '|', '\t', 'total', 'subtotal', '---', '==='
        ]
    
    def chunk_financial_document(self, document) -> List:
        """Chunk financial document preserving calculations and relationships"""
        
        content = document.content
        
        # First, identify financial elements
        elements = self._identify_financial_elements(content)
        
        if not elements:
            # No special financial structure, use time-based chunking
            return self._chunk_by_time_periods(content, document)
        
        # Group elements by calculation dependencies
        calculation_groups = self._group_by_dependencies(elements)
        
        chunks = []
        for group in calculation_groups:
            chunk_content = self._build_calculation_chunk(group, content)
            
            if len(chunk_content.strip()) > 50:
                chunk = self._create_financial_chunk(
                    chunk_content,
                    document,
                    len(chunks),
                    group
                )
                chunks.append(chunk)
        
        return chunks
    
    def _identify_financial_elements(self, content: str) -> List[FinancialElement]:
        """Identify financial elements in content"""
        
        elements = []
        
        # Find calculations
        for pattern in self.calculation_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                element = FinancialElement(
                    element_type='calculation',
                    content=match.group(),
                    dependencies=self._extract_dependencies(match.group()),
                    position=(match.start(), match.end())
                )
                elements.append(element)
        
        # Find metrics
        for pattern in self.metric_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                element = FinancialElement(
                    element_type='metric',
                    content=match.group(),
                    dependencies=[],
                    position=(match.start(), match.end())
                )
                elements.append(element)
        
        return elements
    
    def _extract_dependencies(self, calculation: str) -> List[str]:
        """Extract variable dependencies from calculation"""
        
        # Simple dependency extraction - could be enhanced
        variables = re.findall(r'\b[A-Za-z][A-Za-z0-9_]*\b', calculation)
        return [var for var in variables if var.lower() not in ['sum', 'average', 'total']]
    
    def _group_by_dependencies(self, elements: List[FinancialElement]) -> List[List[FinancialElement]]:
        """Group elements by their dependencies"""
        
        # Simple grouping - in practice, would need more sophisticated dependency analysis
        groups = []
        used_elements = set()
        
        for element in elements:
            if id(element) in used_elements:
                continue
                
            group = [element]
            used_elements.add(id(element))
            
            # Find related elements
            for other in elements:
                if id(other) not in used_elements:
                    # Check if elements are related by position or dependencies
                    if self._are_related(element, other):
                        group.append(other)
                        used_elements.add(id(other))
            
            groups.append(group)
        
        return groups
    
    def _are_related(self, elem1: FinancialElement, elem2: FinancialElement) -> bool:
        """Check if two elements are related"""
        
        # Close proximity
        if abs(elem1.position[0] - elem2.position[0]) < 500:
            return True
        
        # Shared dependencies
        if set(elem1.dependencies) & set(elem2.dependencies):
            return True
        
        return False
    
    def _build_calculation_chunk(self, group: List[FinancialElement], content: str) -> str:
        """Build chunk content for calculation group"""
        
        # Find the span covering all elements in the group
        min_pos = min(elem.position[0] for elem in group)
        max_pos = max(elem.position[1] for elem in group)
        
        # Expand to include context
        context_start = max(0, min_pos - 200)
        context_end = min(len(content), max_pos + 200)
        
        # Align to sentence boundaries
        while context_start > 0 and content[context_start] not in '.!?\n':
            context_start -= 1
        
        while context_end < len(content) and content[context_end] not in '.!?\n':
            context_end += 1
        
        return content[context_start:context_end]
    
    def _chunk_by_time_periods(self, content: str, document) -> List:
        """Fallback: chunk by time periods when no calculations found"""
        
        # Look for time period markers
        time_markers = list(re.finditer(
            r'\b(q[1-4]\s+\d{4}|quarter\s+\d|fy\s*\d{2,4}|fiscal\s+year\s+\d{4})\b',
            content,
            re.IGNORECASE
        ))
        
        if len(time_markers) < 2:
            # No clear time structure, use standard chunking
            return self._standard_chunk(content, document)
        
        chunks = []
        for i, marker in enumerate(time_markers):
            start = marker.start()
            end = time_markers[i + 1].start() if i + 1 < len(time_markers) else len(content)
            
            chunk_content = content[start:end].strip()
            if len(chunk_content) > 100:
                chunk = self._create_financial_chunk(
                    chunk_content,
                    document,
                    i,
                    []
                )
                chunks.append(chunk)
        
        return chunks
    
    def _create_financial_chunk(self, content: str, document, index: int, elements: List[FinancialElement]):
        """Create a financial chunk with appropriate metadata"""
        
        # This would need to return a DocumentChunk instance
        # For now, returning a dict structure
        return {
            'content': content,
            'source_document_id': document.id,
            'chunk_index': index,
            'metadata': {
                'document_type': 'financial',
                'contains_calculations': len([e for e in elements if e.element_type == 'calculation']) > 0,
                'contains_metrics': len([e for e in elements if e.element_type == 'metric']) > 0,
                'financial_elements': len(elements),
                'requires_calculation_review': True
            }
        }
    
    def _standard_chunk(self, content: str, document) -> List:
        """Standard chunking fallback"""
        
        # Simple paragraph-based chunking for financial content
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk + para) < self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunk = self._create_financial_chunk(
                        current_chunk.strip(),
                        document,
                        len(chunks),
                        []
                    )
                    chunks.append(chunk)
                current_chunk = para + "\n\n"
        
        # Last chunk
        if current_chunk.strip():
            chunk = self._create_financial_chunk(
                current_chunk.strip(),
                document,
                len(chunks),
                []
            )
            chunks.append(chunk)
        
        return chunks