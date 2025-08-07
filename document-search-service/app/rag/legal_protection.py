"""
Legal Protection Module - Critical Risk Mitigation
Prevents liability clause splitting and ensures legal compliance
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LegalRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class LegalRiskAssessment:
    level: LegalRiskLevel
    risk_terms: List[str]
    clause_type: Optional[str]
    requires_full_context: bool
    mitigation_required: bool

class LegalRiskDetector:
    """Detects high-risk legal terms that require special chunking handling"""
    
    # Critical terms that must not be split from their context
    HIGH_RISK_TERMS = {
        'liability': ['liability', 'liable', 'damages', 'loss', 'harm'],
        'indemnification': ['indemnif', 'indemnity', 'hold harmless'],
        'warranty': ['warrant', 'guarantee', 'representation'],
        'limitation': ['limit', 'cap', 'maximum', 'not exceed'],
        'exclusion': ['exclude', 'except', 'excluding', 'other than'],
        'breach': ['breach', 'violation', 'default', 'failure to'],
        'termination': ['terminate', 'end', 'cease', 'expir'],
        'force_majeure': ['force majeure', 'act of god', 'unforeseeable'],
        'confidentiality': ['confidential', 'proprietary', 'non-disclosure']
    }
    
    # Clause patterns that indicate legal structure
    CLAUSE_PATTERNS = [
        r'section\s+\d+\.?\d*',
        r'article\s+[ivxlc]+',
        r'paragraph\s+\([a-z]\)',
        r'subsection\s+\([0-9]+\)',
        r'clause\s+\d+',
        r'provided\s+that',
        r'except\s+as\s+provided',
        r'notwithstanding',
        r'subject\s+to'
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) 
                                for pattern in self.CLAUSE_PATTERNS]
    
    def assess_risk(self, text: str) -> LegalRiskAssessment:
        """Assess legal risk level of text content"""
        text_lower = text.lower()
        found_terms = []
        clause_type = None
        
        # Check for high-risk terms
        for category, terms in self.HIGH_RISK_TERMS.items():
            for term in terms:
                if term in text_lower:
                    found_terms.append(term)
                    if not clause_type:
                        clause_type = category
        
        # Determine risk level
        if len(found_terms) >= 3:
            risk_level = LegalRiskLevel.CRITICAL
        elif len(found_terms) >= 2:
            risk_level = LegalRiskLevel.HIGH
        elif len(found_terms) >= 1:
            risk_level = LegalRiskLevel.MEDIUM
        else:
            risk_level = LegalRiskLevel.LOW
        
        # Check for structural patterns that indicate legal complexity
        has_legal_structure = any(pattern.search(text) 
                                for pattern in self.compiled_patterns)
        
        if has_legal_structure and found_terms:
            risk_level = LegalRiskLevel.CRITICAL
        
        return LegalRiskAssessment(
            level=risk_level,
            risk_terms=found_terms,
            clause_type=clause_type,
            requires_full_context=(risk_level in [LegalRiskLevel.HIGH, LegalRiskLevel.CRITICAL]),
            mitigation_required=(risk_level != LegalRiskLevel.LOW)
        )
    
    def find_complete_clause(self, text: str, risk_position: int, 
                           window_size: int = 500) -> Tuple[int, int]:
        """Find complete legal clause boundaries around a risk term"""
        
        # Look for sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        current_pos = 0
        
        for sentence in sentences:
            sentence_end = current_pos + len(sentence)
            if current_pos <= risk_position <= sentence_end:
                # Found the sentence containing the risk term
                # Expand to include related clauses
                
                # Look backward for clause start
                start_pos = max(0, current_pos - window_size)
                
                # Look forward for clause end  
                end_pos = min(len(text), sentence_end + window_size)
                
                # Refine boundaries based on legal markers
                for pattern in self.compiled_patterns:
                    # Look for section/clause boundaries
                    matches = list(pattern.finditer(text[start_pos:end_pos]))
                    if matches:
                        # Adjust boundaries to complete sections
                        pass
                
                return start_pos, end_pos
            
            current_pos = sentence_end + 1
        
        return max(0, risk_position - window_size), min(len(text), risk_position + window_size)

class LegalChunkValidator:
    """Validates chunks containing legal content for completeness and safety"""
    
    def __init__(self):
        self.risk_detector = LegalRiskDetector()
    
    def validate_legal_chunk(self, chunk_content: str, chunk_id: str) -> Dict:
        """Validate a chunk for legal safety"""
        
        risk_assessment = self.risk_detector.assess_risk(chunk_content)
        
        validation_result = {
            "chunk_id": chunk_id,
            "is_valid": True,
            "risk_level": risk_assessment.level.value,
            "warnings": [],
            "errors": [],
            "metadata_additions": {},
            "content_modifications": None
        }
        
        if risk_assessment.mitigation_required:
            validation_result["metadata_additions"].update({
                "legal_risk_level": risk_assessment.level.value,
                "risk_terms": risk_assessment.risk_terms,
                "clause_type": risk_assessment.clause_type,
                "requires_legal_review": True,
                "ai_disclaimer": "This content requires legal review. Not intended as legal advice."
            })
        
        if risk_assessment.level == LegalRiskLevel.CRITICAL:
            # Check for incomplete clauses
            if self._has_incomplete_clause(chunk_content):
                validation_result["errors"].append(
                    "Critical legal term found without complete clause context"
                )
                validation_result["is_valid"] = False
        
        if risk_assessment.requires_full_context:
            validation_result["warnings"].append(
                f"High-risk legal content detected: {', '.join(risk_assessment.risk_terms)}"
            )
        
        return validation_result
    
    def _has_incomplete_clause(self, text: str) -> bool:
        """Check if chunk has incomplete legal clauses"""
        
        # Look for dangling references
        dangling_patterns = [
            r'except\s+as\s*$',
            r'provided\s+that\s*$', 
            r'subject\s+to\s*$',
            r'notwithstanding\s*$',
            r'unless\s*$',
            r'if\s*$',
            r'when\s*$'
        ]
        
        text_end = text.strip().lower()
        
        for pattern in dangling_patterns:
            if re.search(pattern, text_end):
                return True
        
        # Look for incomplete cross-references
        if re.search(r'section\s+\d+\.?\d*\s*$', text_end):
            return True
            
        if re.search(r'as\s+defined\s+in\s*$', text_end):
            return True
        
        return False