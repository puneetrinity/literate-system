"""
Content Type Router - Enhanced Document Router with Enterprise Controls

This router handles the clean separation between different content types:
- Document search (local files, enterprise data)
- Chat conversations (pure conversational AI)
- Web search blocking and manual activation controls

Key Features:
- Document vs Chat classification with high accuracy
- Enterprise web search policy enforcement
- Manual web search activation controls
- Query analysis and content filtering
- Audit logging for compliance
- User permission management
"""

import re
import hashlib
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set

import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ContentType(Enum):
    """Content type classification"""
    DOCUMENT_SEARCH = "document_search"
    CHAT_ONLY = "chat_only"
    WEB_SEARCH_REQUESTED = "web_search_requested"  # Explicitly requested web search


class WebSearchPolicy(Enum):
    """Web search policy enforcement levels"""
    BLOCKED = "blocked"              # Completely blocked
    MANUAL_ONLY = "manual_only"      # Manual activation required
    ADMIN_APPROVED = "admin_approved"  # Admin permission required
    ALLOWED = "allowed"              # Freely allowed


class ContentClassification(BaseModel):
    """Content type classification result"""
    
    content_type: ContentType = Field(description="Classified content type")
    confidence: float = Field(description="Classification confidence score")
    web_search_policy: WebSearchPolicy = Field(description="Applied web search policy")
    reasoning: List[str] = Field(default_factory=list, description="Classification reasoning")
    
    # Document indicators
    document_keywords_found: List[str] = Field(default_factory=list, description="Document-related keywords found")
    document_confidence: float = Field(default=0.0, description="Document search confidence")
    
    # Web search indicators  
    web_keywords_found: List[str] = Field(default_factory=list, description="Web search keywords found")
    web_search_confidence: float = Field(default=0.0, description="Web search confidence")
    
    # Chat indicators
    chat_confidence: float = Field(default=0.0, description="Chat conversation confidence")
    
    # Enterprise controls
    enterprise_account: bool = Field(default=False, description="Is enterprise account")
    user_permissions: Dict[str, bool] = Field(default_factory=dict, description="User permissions")
    admin_override: Optional[str] = Field(default=None, description="Admin override applied")
    
    # Audit trail
    classification_id: str = Field(description="Unique classification ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Classification timestamp")


class ContentTypeRouter:
    """
    Enhanced router for content type classification with enterprise controls
    """
    
    def __init__(self):
        self._init_classification_patterns()
        self._init_enterprise_policies()
        self._init_filtering_rules()
        
        logger.info("ContentTypeRouter initialized with enterprise controls")
    
    def _init_classification_patterns(self):
        """Initialize content classification patterns"""
        
        # Document search indicators
        self.document_keywords = {
            "explicit_document": [
                "document", "documents", "file", "files", "pdf", "doc", "docx",
                "upload", "uploaded", "my files", "my documents", "in my files",
                "from my documents", "search documents", "find in documents"
            ],
            "document_actions": [
                "what does my document say", "find in files", "search my files",
                "from the document", "in the uploaded file", "document contains",
                "file shows", "according to my document"
            ],
            "file_references": [
                "the document", "this file", "that document", "uploaded file",
                "my file", "our document", "company document", "internal document"
            ]
        }
        
        # Web search indicators
        self.web_keywords = {
            "explicit_web": [
                "search web", "web search", "search online", "search internet",
                "google", "bing", "search for", "look up online"
            ],
            "temporal_indicators": [
                "latest", "recent", "current", "today", "now", "up to date",
                "breaking", "news", "trending", "this week", "this month"
            ],
            "external_info": [
                "what's happening", "current events", "market news", "stock price",
                "weather", "sports scores", "cryptocurrency price", "exchange rate"
            ]
        }
        
        # Chat conversation indicators
        self.chat_keywords = {
            "conversational": [
                "hello", "hi", "hey", "thanks", "thank you", "goodbye", "bye",
                "how are you", "what's up", "nice to meet", "please", "sorry"
            ],
            "explanatory": [
                "explain", "tell me about", "what is", "how does", "why",
                "can you help", "help me understand", "what do you think"
            ],
            "general_knowledge": [
                "define", "meaning of", "difference between", "pros and cons",
                "advantages", "disadvantages", "best practices", "how to"
            ]
        }
    
    def _init_enterprise_policies(self):
        """Initialize enterprise policy rules"""
        
        # Default enterprise policies
        self.enterprise_policies = {
            "default_web_search_policy": WebSearchPolicy.MANUAL_ONLY,
            "require_double_consent": True,
            "log_all_web_requests": True,
            "block_sensitive_queries": True,
            "require_admin_approval_for_research": False
        }
        
        # Sensitive content patterns that require additional controls
        self.sensitive_patterns = [
            r'\b(confidential|proprietary|internal|classified)\b',
            r'\b(password|secret|key|token|credential)\b',
            r'\b(financial|salary|budget|cost|revenue)\b',
            r'\b(personal|private|pii|ssn|credit card)\b'
        ]
    
    def _init_filtering_rules(self):
        """Initialize content filtering rules"""
        
        # Query filtering patterns
        self.filter_patterns = {
            "document_prefixes": [
                "in my document", "from my file", "search my documents",
                "find in files", "according to my document"
            ],
            "web_prefixes": [
                "search web for", "look up online", "find on internet",
                "web search", "google"
            ],
            "command_patterns": [
                r'^search\s+web:\s*(.+)$',
                r'^search\s+docs?:\s*(.+)$', 
                r'^find\s+in\s+files:\s*(.+)$'
            ]
        }
    
    async def classify_content_type(self,
                                  query: str,
                                  user_id: Optional[str] = None,
                                  session_id: Optional[str] = None,
                                  user_permissions: Optional[Dict[str, bool]] = None,
                                  enterprise_account: bool = False,
                                  admin_override: Optional[str] = None) -> ContentClassification:
        """
        Classify content type with enterprise controls and policy enforcement
        """
        
        classification_id = hashlib.md5(f"{query}{user_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        reasoning = []
        
        # 1. Extract and analyze query features
        query_lower = query.lower().strip()
        features = self._extract_content_features(query_lower)
        reasoning.append(f"Extracted {len(features)} content features")
        
        # 2. Command pattern detection
        command_type = self._detect_command_patterns(query_lower)
        if command_type:
            reasoning.append(f"Command pattern detected: {command_type}")
        
        # 3. Document content analysis
        doc_confidence, doc_keywords = self._analyze_document_indicators(query_lower)
        reasoning.append(f"Document confidence: {doc_confidence:.2f}")
        
        # 4. Web search analysis
        web_confidence, web_keywords = self._analyze_web_indicators(query_lower)
        reasoning.append(f"Web search confidence: {web_confidence:.2f}")
        
        # 5. Chat conversation analysis
        chat_confidence = self._analyze_chat_indicators(query_lower)
        reasoning.append(f"Chat confidence: {chat_confidence:.2f}")
        
        # 6. Sensitive content detection
        is_sensitive = self._detect_sensitive_content(query_lower)
        if is_sensitive:
            reasoning.append("Sensitive content detected - additional controls applied")
        
        # 7. Determine primary content type
        content_type = self._determine_content_type(
            doc_confidence, web_confidence, chat_confidence, command_type
        )
        reasoning.append(f"Primary content type: {content_type.value}")
        
        # 8. Apply enterprise policy
        web_search_policy = self._apply_enterprise_policy(
            content_type, enterprise_account, is_sensitive, user_permissions
        )
        reasoning.append(f"Web search policy: {web_search_policy.value}")
        
        # 9. Handle admin overrides
        if admin_override:
            content_type, web_search_policy = self._apply_admin_override(
                admin_override, content_type, web_search_policy
            )
            reasoning.append(f"Admin override applied: {admin_override}")
        
        # 10. Calculate overall confidence
        confidence_scores = [doc_confidence, web_confidence, chat_confidence]
        overall_confidence = max(confidence_scores) if confidence_scores else 0.5
        
        # Create classification result
        classification = ContentClassification(
            content_type=content_type,
            confidence=overall_confidence,
            web_search_policy=web_search_policy,
            reasoning=reasoning,
            document_keywords_found=doc_keywords,
            document_confidence=doc_confidence,
            web_keywords_found=web_keywords,
            web_search_confidence=web_confidence,
            chat_confidence=chat_confidence,
            enterprise_account=enterprise_account,
            user_permissions=user_permissions or {},
            admin_override=admin_override,
            classification_id=classification_id
        )
        
        # Log classification for audit trail
        await self._log_classification(classification, query, user_id, session_id)
        
        return classification
    
    def _extract_content_features(self, query: str) -> Dict[str, float]:
        """Extract content-specific features from query"""
        
        features = {
            "length": min(len(query) / 100.0, 1.0),
            "question_marks": min(query.count('?') / 3.0, 1.0),
            "technical_terms": len(re.findall(r'\b(api|database|algorithm|code|programming)\b', query)) / 10.0,
            "temporal_terms": len(re.findall(r'\b(latest|recent|current|today|now|new)\b', query)) / 5.0,
            "file_references": len(re.findall(r'\b(file|document|pdf|doc|upload)\b', query)) / 5.0,
            "search_terms": len(re.findall(r'\b(search|find|lookup|locate)\b', query)) / 5.0
        }
        
        # Normalize all features to 0-1 range
        for key in features:
            features[key] = min(features[key], 1.0)
        
        return features
    
    def _detect_command_patterns(self, query: str) -> Optional[str]:
        """Detect explicit command patterns in query"""
        
        for pattern in self.filter_patterns["command_patterns"]:
            match = re.search(pattern, query)
            if match:
                if "web" in pattern:
                    return "web_command"
                elif "doc" in pattern or "file" in pattern:
                    return "document_command"
        
        # Check for prefix patterns
        for prefix in self.filter_patterns["web_prefixes"]:
            if query.startswith(prefix.lower()):
                return "web_prefix"
        
        for prefix in self.filter_patterns["document_prefixes"]:
            if query.startswith(prefix.lower()):
                return "document_prefix"
        
        return None
    
    def _analyze_document_indicators(self, query: str) -> Tuple[float, List[str]]:
        """Analyze document search indicators"""
        
        found_keywords = []
        score = 0.0
        
        # Check all document keyword categories
        for category, keywords in self.document_keywords.items():
            category_score = 0.0
            for keyword in keywords:
                if keyword in query:
                    found_keywords.append(keyword)
                    category_score += 1.0
            
            # Weight different categories
            if category == "explicit_document":
                score += category_score * 0.8
            elif category == "document_actions":
                score += category_score * 1.0
            elif category == "file_references":
                score += category_score * 0.6
        
        # Normalize score
        confidence = min(score / 5.0, 1.0)
        
        return confidence, found_keywords
    
    def _analyze_web_indicators(self, query: str) -> Tuple[float, List[str]]:
        """Analyze web search indicators"""
        
        found_keywords = []
        score = 0.0
        
        # Check all web keyword categories
        for category, keywords in self.web_keywords.items():
            category_score = 0.0
            for keyword in keywords:
                if keyword in query:
                    found_keywords.append(keyword)
                    category_score += 1.0
            
            # Weight different categories
            if category == "explicit_web":
                score += category_score * 1.0
            elif category == "temporal_indicators":
                score += category_score * 0.7
            elif category == "external_info":
                score += category_score * 0.8
        
        # Normalize score
        confidence = min(score / 5.0, 1.0)
        
        return confidence, found_keywords
    
    def _analyze_chat_indicators(self, query: str) -> float:
        """Analyze chat conversation indicators"""
        
        score = 0.0
        
        # Check all chat keyword categories  
        for category, keywords in self.chat_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    if category == "conversational":
                        score += 0.8
                    elif category == "explanatory":
                        score += 0.6
                    elif category == "general_knowledge":
                        score += 0.5
        
        # Boost score for question patterns
        if query.endswith('?') and not any(web_word in query for web_word in ["latest", "current", "recent"]):
            score += 0.3
        
        # Normalize score
        confidence = min(score / 3.0, 1.0)
        
        return confidence
    
    def _detect_sensitive_content(self, query: str) -> bool:
        """Detect sensitive content that requires additional controls"""
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        return False
    
    def _determine_content_type(self, doc_confidence: float, web_confidence: float, 
                               chat_confidence: float, command_type: Optional[str]) -> ContentType:
        """Determine primary content type from analysis"""
        
        # Command patterns take highest precedence
        if command_type:
            if "web" in command_type:
                return ContentType.WEB_SEARCH_REQUESTED
            elif "document" in command_type:
                return ContentType.DOCUMENT_SEARCH
        
        # Confidence-based determination
        max_confidence = max(doc_confidence, web_confidence, chat_confidence)
        
        if doc_confidence == max_confidence and doc_confidence > 0.4:
            return ContentType.DOCUMENT_SEARCH
        elif web_confidence == max_confidence and web_confidence > 0.4:
            return ContentType.WEB_SEARCH_REQUESTED
        else:
            return ContentType.CHAT_ONLY
    
    def _apply_enterprise_policy(self, content_type: ContentType, enterprise_account: bool,
                                is_sensitive: bool, user_permissions: Optional[Dict[str, bool]]) -> WebSearchPolicy:
        """Apply enterprise policy to determine web search permissions"""
        
        # Default policy for non-enterprise accounts
        if not enterprise_account:
            if content_type == ContentType.WEB_SEARCH_REQUESTED:
                return WebSearchPolicy.MANUAL_ONLY
            else:
                return WebSearchPolicy.BLOCKED
        
        # Enterprise account policies
        user_perms = user_permissions or {}
        
        # Check if user has web search permissions
        if not user_perms.get("web_search_enabled", False):
            return WebSearchPolicy.BLOCKED
        
        # Sensitive content requires admin approval
        if is_sensitive and self.enterprise_policies["require_admin_approval_for_research"]:
            return WebSearchPolicy.ADMIN_APPROVED
        
        # Default enterprise policy
        if content_type == ContentType.WEB_SEARCH_REQUESTED:
            return self.enterprise_policies["default_web_search_policy"]
        else:
            return WebSearchPolicy.BLOCKED
    
    def _apply_admin_override(self, admin_override: str, current_type: ContentType, 
                             current_policy: WebSearchPolicy) -> Tuple[ContentType, WebSearchPolicy]:
        """Apply admin override to content type and policy"""
        
        override_lower = admin_override.lower()
        
        if override_lower in ["allow_web", "enable_web_search"]:
            return ContentType.WEB_SEARCH_REQUESTED, WebSearchPolicy.ALLOWED
        elif override_lower in ["force_document", "document_only"]:
            return ContentType.DOCUMENT_SEARCH, WebSearchPolicy.BLOCKED
        elif override_lower in ["chat_only", "disable_search"]:
            return ContentType.CHAT_ONLY, WebSearchPolicy.BLOCKED
        elif override_lower in ["manual_web", "require_consent"]:
            return current_type, WebSearchPolicy.MANUAL_ONLY
        
        # Unknown override - keep current settings
        return current_type, current_policy
    
    async def _log_classification(self, classification: ContentClassification, query: str,
                                 user_id: Optional[str], session_id: Optional[str]):
        """Log classification for audit trail and compliance"""
        
        log_entry = {
            "classification_id": classification.classification_id,
            "timestamp": classification.timestamp.isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "query_hash": hashlib.md5(query.encode()).hexdigest(),
            "content_type": classification.content_type.value,
            "web_search_policy": classification.web_search_policy.value,
            "confidence": classification.confidence,
            "enterprise_account": classification.enterprise_account,
            "admin_override": classification.admin_override,
            "reasoning": classification.reasoning
        }
        
        # Log for monitoring and compliance
        logger.info("Content classification completed", **log_entry)
        
        # Store in audit database (would be implemented based on requirements)
        # await self._store_audit_record(log_entry)
    
    def check_web_search_permission(self, classification: ContentClassification,
                                   user_consent: bool = False,
                                   admin_approval: bool = False) -> Tuple[bool, str]:
        """Check if web search is permitted based on classification and user context"""
        
        policy = classification.web_search_policy
        
        if policy == WebSearchPolicy.BLOCKED:
            return False, "Web search is blocked by enterprise policy"
        
        elif policy == WebSearchPolicy.ALLOWED:
            return True, "Web search allowed"
        
        elif policy == WebSearchPolicy.MANUAL_ONLY:
            if user_consent:
                return True, "Web search allowed with user consent"
            else:
                return False, "Web search requires explicit user consent"
        
        elif policy == WebSearchPolicy.ADMIN_APPROVED:
            if admin_approval:
                return True, "Web search allowed with admin approval"
            else:
                return False, "Web search requires administrator approval"
        
        return False, "Unknown web search policy"
    
    def extract_filtered_query(self, query: str, classification: ContentClassification) -> str:
        """Extract and filter query based on content type classification"""
        
        # Remove command prefixes if present
        filtered_query = query.strip()
        
        # Handle command patterns
        for pattern in self.filter_patterns["command_patterns"]:
            match = re.search(pattern, filtered_query, re.IGNORECASE)
            if match:
                filtered_query = match.group(1).strip()
                break
        
        # Remove explicit prefixes
        for prefix in self.filter_patterns["web_prefixes"] + self.filter_patterns["document_prefixes"]:
            if filtered_query.lower().startswith(prefix.lower()):
                filtered_query = filtered_query[len(prefix):].strip()
                break
        
        return filtered_query if filtered_query else query