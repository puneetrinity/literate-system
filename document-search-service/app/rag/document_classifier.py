"""
Advanced Document Classification for Type-Specific Chunking
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import mimetypes

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    LEGAL = "legal"
    FINANCIAL = "financial"
    CODE = "code"
    TECHNICAL = "technical"
    CONVERSATION = "conversation"
    GENERAL = "general"

@dataclass
class ClassificationResult:
    document_type: DocumentType
    confidence: float
    detected_features: List[str]
    suggested_chunk_size: int
    suggested_overlap: int

class AdvancedDocumentClassifier:
    """Advanced document classification using multiple signals"""
    
    def __init__(self):
        self.classification_rules = {
            DocumentType.LEGAL: {
                'filename_patterns': [
                    r'.*\b(contract|agreement|nda|terms|license|legal)\b.*',
                    r'.*\.(doc|docx|pdf)$'
                ],
                'content_patterns': [
                    r'\b(whereas|party\s+[ab]|indemnif|liability|agreement|contract)\b',
                    r'\bsection\s+\d+\.?\d*\b',
                    r'\barticle\s+[ivxlc]+\b',
                    r'\b(shall|will|agrees?|represents?)\b',
                    r'\b(terms\s+and\s+conditions|privacy\s+policy)\b'
                ],
                'structural_features': [
                    'numbered_sections',
                    'signature_blocks',
                    'legal_entities'
                ],
                'chunk_size': 800,
                'overlap': 100
            },
            DocumentType.FINANCIAL: {
                'filename_patterns': [
                    r'.*\b(financial|budget|report|statement|earnings)\b.*',
                    r'.*\.(xlsx?|csv)$'
                ],
                'content_patterns': [
                    r'\$[\d,]+\.?\d*',
                    r'\b(revenue|profit|loss|ebitda|balance\s+sheet)\b',
                    r'\b(quarterly|q[1-4]|fiscal\s+year|fy\d{2,4})\b',
                    r'\b\d+\.?\d*%\b',
                    r'\b(million|billion|thousand)\b'
                ],
                'structural_features': [
                    'tables',
                    'calculations',
                    'percentages'
                ],
                'chunk_size': 1000,
                'overlap': 150
            },
            DocumentType.CODE: {
                'filename_patterns': [
                    r'.*\.(py|js|java|cpp|c|rb|php|go|rs|ts)$'
                ],
                'content_patterns': [
                    r'\b(function|def|class|import|require)\b',
                    r'\b(if|else|for|while|try|catch)\b',
                    r'\b(return|yield|async|await)\b',
                    r'[{}\[\]();]'
                ],
                'structural_features': [
                    'functions',
                    'classes',
                    'imports'
                ],
                'chunk_size': 500,
                'overlap': 50
            },
            DocumentType.TECHNICAL: {
                'filename_patterns': [
                    r'.*\b(manual|guide|documentation|readme|api)\b.*',
                    r'.*\.md$'
                ],
                'content_patterns': [
                    r'#{1,6}\s+[A-Z]',  # Markdown headers
                    r'\b(configure|install|setup|parameter)\b',
                    r'\b(version|release|update)\b',
                    r'```[\s\S]*?```'  # Code blocks
                ],
                'structural_features': [
                    'headers',
                    'code_blocks',
                    'lists'
                ],
                'chunk_size': 700,
                'overlap': 70
            },
            DocumentType.CONVERSATION: {
                'filename_patterns': [
                    r'.*\b(chat|conversation|transcript|meeting)\b.*'
                ],
                'content_patterns': [
                    r'^[A-Z][a-z]+\s*:\s*',  # Speaker: format
                    r'\b(said|replied|asked|answered)\b',
                    r'\[\d{2}:\d{2}\]',  # Timestamps
                    r'\b(um|uh|yeah|okay)\b'  # Conversational fillers
                ],
                'structural_features': [
                    'speaker_turns',
                    'timestamps',
                    'dialogue'
                ],
                'chunk_size': 600,
                'overlap': 80
            }
        }
    
    def classify_document(self, document) -> ClassificationResult:
        """Classify document type using multiple signals"""
        
        filename = getattr(document, 'filename', '') or ''
        content = document.content[:2000].lower()  # First 2K chars for classification
        
        scores = {}
        detected_features = {}
        
        for doc_type, rules in self.classification_rules.items():
            score = 0
            features = []
            
            # Filename pattern matching
            for pattern in rules['filename_patterns']:
                if re.search(pattern, filename.lower(), re.IGNORECASE):
                    score += 3
                    features.append(f"filename_match:{pattern}")
            
            # Content pattern matching
            content_matches = 0
            for pattern in rules['content_patterns']:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                content_matches += matches
                if matches > 0:
                    features.append(f"content_match:{pattern}:{matches}")
            
            # Weight content matches
            score += min(content_matches * 0.5, 5)  # Cap at 5 points
            
            # Structural feature detection
            structure_score = self._detect_structural_features(content, rules['structural_features'])
            score += structure_score
            features.extend([f"structure:{feature}" for feature in rules['structural_features']])
            
            scores[doc_type] = score
            detected_features[doc_type] = features
        
        # Find best match
        if not scores or max(scores.values()) == 0:
            return ClassificationResult(
                document_type=DocumentType.GENERAL,
                confidence=0.0,
                detected_features=[],
                suggested_chunk_size=600,
                suggested_overlap=60
            )
        
        best_type = max(scores.items(), key=lambda x: x[1])[0]
        confidence = scores[best_type] / (sum(scores.values()) + 0.001)  # Avoid division by zero
        
        rules = self.classification_rules[best_type]
        
        return ClassificationResult(
            document_type=best_type,
            confidence=confidence,
            detected_features=detected_features[best_type],
            suggested_chunk_size=rules['chunk_size'],
            suggested_overlap=rules['overlap']
        )
    
    def _detect_structural_features(self, content: str, features: List[str]) -> float:
        """Detect structural features in content"""
        
        score = 0
        
        for feature in features:
            if feature == 'numbered_sections':
                if re.search(r'^\d+\.?\s+[A-Z]', content, re.MULTILINE):
                    score += 1
            elif feature == 'signature_blocks':
                if re.search(r'\b(signature|signed|date)\b.*\n.*\n', content):
                    score += 1
            elif feature == 'tables':
                if content.count('|') > 5 or content.count('\t') > 10:
                    score += 1
            elif feature == 'calculations':
                if re.search(r'[=+\-*/]', content):
                    score += 1
            elif feature == 'functions':
                if re.search(r'\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(', content):
                    score += 1
            elif feature == 'classes':
                if re.search(r'\bclass\s+\w+', content):
                    score += 1
            elif feature == 'speaker_turns':
                speaker_pattern = r'^[A-Z][a-z]+\s*:\s*'
                if len(re.findall(speaker_pattern, content, re.MULTILINE)) > 2:
                    score += 1
        
        return score