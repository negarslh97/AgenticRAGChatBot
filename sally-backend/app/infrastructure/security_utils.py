#security_utils.py

"""
Advanced security utilities for AI applications with modern protection mechanisms.
"""

import re
import html
import hashlib
import hmac
import secrets
import unicodedata
from typing import List, Dict, Any, Optional, Set, Pattern
from dataclasses import dataclass
from enum import Enum
import logging
from urllib.parse import urlparse
import json
from datetime import datetime, timedelta
import bleach

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security levels for different protection mechanisms."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    level: SecurityLevel = SecurityLevel.STANDARD
    max_input_length: int = 10000
    allowed_tags: Set[str] = None
    allowed_attributes: Dict[str, Set[str]] = None
    max_token_limit: int = 8192
    enable_sanitize_html: bool = True
    enable_sanitize_urls: bool = True
    enable_sanitize_json: bool = True
    enable_rate_limiting: bool = True
    max_repeated_chars: int = 5
    detect_prompt_injection: bool = True
    detect_sql_injection: bool = True
    detect_xss: bool = True
    
    def __post_init__(self):
        if self.allowed_tags is None:
            self.allowed_tags = {'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre'}
        
        if self.allowed_attributes is None:
            self.allowed_attributes = {
                'p': set(),
                'br': set(),
                'strong': set(),
                'em': set(),
                'u': set(),
                'h1': set(), 'h2': set(), 'h3': set(), 'h4': set(), 'h5': set(), 'h6': set(),
                'ul': set(), 'ol': set(), 'li': set(),
                'blockquote': set(),
                'code': {'class'},
                'pre': {'class'}
            }


class PromptInjectionDetector:
    """Advanced prompt injection detection system."""
    
    def __init__(self, security_config: SecurityConfig):
        self.config = security_config
        self._suspicious_patterns = self._load_suspicious_patterns()
        self._whitelist_patterns = self._load_whitelist_patterns()
    
    def _load_suspicious_patterns(self) -> Pattern:
        """Load suspicious patterns for prompt injection detection - optimized single pattern."""
        # Combine all patterns into a single regex for better performance
        pattern = r"""
            (ignore\s+previous\s+instructions|
            disregard\s+everything\s+above|
            forget\s+everything\s+i\s+said|
            start\s+over|
            restart\s+from\s+beginning|
            
            you\s+are\s+now|
            you\s+are\s+a|
            act\s+as|
            pretend\s+to\s+be|
            become|
            
            system\s+prompt|
            initial\s+instructions|
            original\s+prompt|
            
            dan\s+mode|
            evil\s+mode|
            jailbreak|
            uncensored|
            
            output\s+format|
            response\s+format|
            json\s+format|
            xml\s+format|
            
            exec\s*\(|eval\s*\(|__import__|subprocess\.|os\.|system\s*\(|open\s*\(|file\s+|read\s+file|write\s+file|
            
            http|www\.|\.com|\.org|\.net|
            
            extract\s+data|send\s+to|upload\s+to|export\s+data|
            
            remember\s+this|save\s+this|store\s+this|keep\s+in\s+memory|
            
            context|conversation|history|previous)
        """
        return re.compile(pattern, re.IGNORECASE | re.VERBOSE)
    
    def _load_whitelist_patterns(self) -> Pattern:
        """Load whitelist patterns for false positive reduction - optimized single pattern."""
        # Combine all whitelist patterns into a single regex for better performance
        pattern = r"""
            (hello\s+world|
            print\s+hello\s+world|
            hello\s+everyone|
            good\s+morning|
            good\s+afternoon|
            good\s+evening|
            please\s+help|
            can\s+you\s+help|
            how\s+to|
            what\s+is|
            where\s+is|
            when\s+is|
            why\s+is|
            who\s+is)
        """
        return re.compile(pattern, re.IGNORECASE | re.VERBOSE)
    
    def detect_injection(self, text: str) -> Dict[str, Any]:
        """Detect prompt injection attempts in text."""
        if not self.config.detect_prompt_injection:
            return {"detected": False, "risk_score": 0, "matches": []}
        
        text_lower = text.lower()
        matches = []
        risk_score = 0
        
        # Check against suspicious patterns (optimized single pattern)
        pattern_matches = self._suspicious_patterns.findall(text_lower)
        if pattern_matches:
            matches.extend([
                {
                    "pattern": match,
                    "matches": [match],
                    "risk": self._calculate_pattern_risk(match)
                }
                for match in set(pattern_matches)  # Remove duplicates
            ])
            risk_score += sum(self._calculate_pattern_risk(match) for match in set(pattern_matches))
        
        # Check against whitelist to reduce false positives (optimized single pattern)
        if self._whitelist_patterns.search(text_lower):
            risk_score *= 0.5  # Reduce risk if whitelist pattern matches
        
        # Additional risk factors
        if len(text) > 1000:
            risk_score += 0.1
        
        if self._contains_suspicious_repetition(text):
            risk_score += 0.2
        
        if self._contains_suspicious_capitalization(text):
            risk_score += 0.15
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        
        detection_result = {
            "detected": risk_score > 0.35,
            "risk_score": risk_score,
            "matches": matches,
            "text_length": len(text),
            "suspicious_patterns_count": len(matches)
        }
        
        if detection_result["detected"]:
            logger.warning(f"Prompt injection detected with risk score: {risk_score:.2f}")
        
        return detection_result
    
    def _calculate_pattern_risk(self, pattern: str) -> float:
        """Calculate risk score for a pattern."""
        high_risk_patterns = [
            r'ignore\s+previous\s+instructions',
            r'disregard\s+everything\s+above',
            r'dan\s+mode',
            r'evil\s+mode',
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__'
        ]

        if any(high_risk in pattern.lower() for high_risk in high_risk_patterns):
            return 0.3

        medium_risk_patterns = [
            r'system\s+prompt',
            r'pretend\s+to\s+be',
            r'become',
            r'output\s+format',
            r'response\s+format',
            r'you\s+are\s+now',  # Moved from high risk
            r'act\s+as',         # Moved from high risk
            r'open\s*\(',
            r'file\s+',
            r'http',
            r'extract\s+data',
            r'remember\s+this'
        ]
        
        if any(medium_risk in pattern.lower() for medium_risk in medium_risk_patterns):
            return 0.15
        
        return 0.05
    
    def _contains_suspicious_repetition(self, text: str) -> bool:
        """Check for suspicious character repetition."""
        for char in set(text):
            if char.isalnum() and text.count(char) > self.config.max_repeated_chars:
                return True
        return False
    
    def _contains_suspicious_capitalization(self, text: str) -> bool:
        """Check for suspicious capitalization patterns."""
        # Check for excessive capitalization
        if len(text) > 10:
            capital_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if capital_ratio > 0.7:
                return True
        
        # Check for alternating case (potential obfuscation)
        if len(text) > 5:
            alternating_case = True
            for i in range(1, len(text) - 1):
                if text[i].isupper() == text[i + 1].isupper():
                    alternating_case = False
                    break
            if alternating_case:
                return True
        
        return False


class InputValidator:
    """Comprehensive input validation system."""
    
    def __init__(self, security_config: SecurityConfig):
        self.config = security_config
        self.injection_detector = PromptInjectionDetector(security_config)
    
    def validate_input(self, text: str, input_type: str = "general") -> Dict[str, Any]:
        """Validate input text comprehensively."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "sanitized_text": text,
            "security_checks": {}
        }
        
        # Length validation
        if len(text) > self.config.max_input_length:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Input exceeds maximum length of {self.config.max_input_length} characters")
            return validation_result
        
        # Prompt injection detection
        injection_result = self.injection_detector.detect_injection(text)
        validation_result["security_checks"]["prompt_injection"] = injection_result
        
        if injection_result["detected"]:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Potential prompt injection detected (risk score: {injection_result['risk_score']:.2f})")
        
        # SQL injection detection
        if self.config.detect_sql_injection:
            sql_injection = self._detect_sql_injection(text)
            validation_result["security_checks"]["sql_injection"] = sql_injection
            
            if sql_injection["detected"]:
                validation_result["valid"] = False
                validation_result["errors"].append("Potential SQL injection detected")
        
        # XSS detection
        if self.config.detect_xss:
            xss_result = self._detect_xss(text)
            validation_result["security_checks"]["xss"] = xss_result
            
            if xss_result["detected"]:
                validation_result["warnings"].append("Potential XSS detected (sanitized)")
        
        # HTML sanitization
        if self.config.enable_sanitize_html:
            sanitized_text = self._sanitize_html(text)
            if sanitized_text != text:
                validation_result["warnings"].append("HTML content was sanitized")
            validation_result["sanitized_text"] = sanitized_text
        
        # URL sanitization
        if self.config.enable_sanitize_urls:
            url_result = self._sanitize_urls(text)
            if url_result["modified"]:
                validation_result["warnings"].append("URL content was sanitized")
            validation_result["security_checks"]["url_sanitization"] = url_result
        
        # JSON validation
        if self.config.enable_sanitize_json and input_type == "json":
            json_result = self._validate_json(text)
            if not json_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].append("Invalid JSON format")
            validation_result["security_checks"]["json_validation"] = json_result
        
        return validation_result
    
    def _detect_sql_injection(self, text: str) -> Dict[str, Any]:
        """Detect SQL injection attempts."""
        sql_patterns = [
            r'union\s+select',
            r'or\s+1\s*=\s*1',
            r'and\s+1\s*=\s*1',
            r'drop\s+table',
            r'insert\s+into',
            r'delete\s+from',
            r'update\s+set',
            r'exec\s*\(',
            r'execute\s*\(',
            r'xp_cmdshell',
            r'sp_oacreate',
            r'sp_addsrvrolemember',
            r'waitfor\s+delay',
            r'--',
            r'/\*.*?\*/',
            r';\s*shutdown',
            r';\s*drop',
            r'create\s+table',
            r'alter\s+table',
            r'truncate\s+table',
            r'grant\s+all',
            r'revoke\s+all'
        ]
        
        detected_patterns = []
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected_patterns.append(pattern)
        
        return {
            "detected": len(detected_patterns) > 0,
            "patterns": detected_patterns,
            "pattern_count": len(detected_patterns)
        }
    
    def _detect_xss(self, text: str) -> Dict[str, Any]:
        """Detect XSS attempts using bleach library for production-grade security."""
        try:
            # First try to clean with bleach - if it detects dangerous content, it will be stripped
            cleaned_text = bleach.clean(
                text,
                tags=[],  # No tags allowed - strip all HTML
                attributes={},  # No attributes allowed
                strip=True  # Strip disallowed content instead of escaping
            )
            
            # If the cleaned text is different from original, XSS was detected
            xss_detected = cleaned_text != text
            
            if xss_detected:
                # Try to identify specific dangerous patterns that were removed
                detected_patterns = []
                
                # Check for common XSS patterns that bleach would catch
                if re.search(r'<script[^>]*>.*?</script>', text, re.IGNORECASE):
                    detected_patterns.append('<script> tags')
                if re.search(r'javascript:', text, re.IGNORECASE):
                    detected_patterns.append('javascript: protocol')
                if re.search(r'on\w+\s*=', text, re.IGNORECASE):
                    detected_patterns.append('event handlers (on*)')
                if re.search(r'eval\s*\(', text, re.IGNORECASE):
                    detected_patterns.append('eval() function')
                if re.search(r'document\.|window\.', text, re.IGNORECASE):
                    detected_patterns.append('DOM access (document/window)')
                
                return {
                    "detected": True,
                    "patterns": detected_patterns,
                    "pattern_count": len(detected_patterns),
                    "cleaned_text": cleaned_text
                }
            
            return {
                "detected": False,
                "patterns": [],
                "pattern_count": 0,
                "cleaned_text": cleaned_text
            }
            
        except Exception as e:
            logger.warning(f"XSS detection with bleach failed: {e}")
            # Fallback to basic regex detection if bleach fails
            return self._detect_xss_fallback(text)
    
    def _detect_xss_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback XSS detection using regex when bleach is unavailable."""
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'document\.',
            r'window\.',
            r'alert\s*\(',
            r'prompt\s*\(',
            r'confirm\s*\(',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*rel=',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'<img[^>]*src=',
            r'<svg[^>]*>',
            r'<math[^>]*>',
            r'expression\s*\(',
            r'@import',
            r'url\s*\(',
            r'behavior:',
            r'binding:',
            r'include-source:',
            r'-moz-binding'
        ]
        
        detected_patterns = []
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected_patterns.append(pattern)
        
        return {
            "detected": len(detected_patterns) > 0,
            "patterns": detected_patterns,
            "pattern_count": len(detected_patterns)
        }
    
    def _sanitize_html(self, text: str) -> str:
        """Sanitize HTML content using bleach library for production-grade security."""
        try:
            # Use bleach to clean HTML with strict security settings
            cleaned_text = bleach.clean(
                text,
                tags=self.config.allowed_tags,
                attributes=self.config.allowed_attributes,
                strip=True,  # Strip disallowed content instead of escaping
                strip_comments=True  # Remove HTML comments
            )
            
            # Escape any remaining HTML entities to prevent double-encoding
            cleaned_text = html.escape(cleaned_text)
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.warning(f"HTML sanitization with bleach failed: {e}")
            # Fallback to basic regex sanitization if bleach fails
            return self._sanitize_html_fallback(text)
    
    def _sanitize_html_fallback(self, text: str) -> str:
        """Fallback HTML sanitization using regex when bleach is unavailable."""
        # Convert HTML entities to characters
        text = html.unescape(text)
        
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _sanitize_urls(self, text: str) -> Dict[str, Any]:
        """Sanitize URLs in text."""
        modified = False
        original_text = text
        
        # Remove potentially dangerous URL schemes
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
        for scheme in dangerous_schemes:
            if scheme in text.lower():
                text = re.sub(f'{scheme}[^\\s<>"\'()]+', '', text, flags=re.IGNORECASE)
                modified = True
        
        # Remove URL parameters that might be malicious
        url_pattern = r'https?://[^\s<>"\'()]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.query:
                    # Remove query parameters that might be malicious
                    safe_params = []
                    for param in parsed.query.split('&'):
                        if not any(malicious in param.lower() for malicious in ['javascript:', 'data:', 'vbscript:']):
                            safe_params.append(param)
                    
                    if safe_params != parsed.query.split('&'):
                        reconstructed_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if safe_params:
                            reconstructed_url += '?' + '&'.join(safe_params)
                        
                        text = text.replace(url, reconstructed_url)
                        modified = True
            except Exception:
                continue
        
        return {
            "modified": modified,
            "original_text": original_text,
            "sanitized_text": text
        }
    
    def _validate_json(self, text: str) -> Dict[str, Any]:
        """Validate JSON format."""
        try:
            json.loads(text)
            return {"valid": True}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e)}


class SecurityManager:
    """Main security manager that coordinates all security operations."""
    
    def __init__(self, security_config: Optional[SecurityConfig] = None, redis_client=None):
        self.config = security_config or SecurityConfig()
        self.validator = InputValidator(self.config)
        self._api_keys = set()
        self._rate_limits = {}
        self._session_tokens = {}
        self._redis_client = redis_client
        self._use_redis = redis_client is not None
        
        # Rate limiting configuration
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 100  # requests per window
    
    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """Validate a prompt for security."""
        return self.validator.validate_input(prompt, "prompt")
    
    def validate_user_input(self, user_input: str) -> Dict[str, Any]:
        """Validate user input for security."""
        return self.validator.validate_input(user_input, "user_input")
    
    def sanitize_output(self, output: str) -> str:
        """Sanitize AI output for security."""
        # Remove thinking blocks
        output = re.sub(r'<thinking>.*?</thinking>', '', output, flags=re.DOTALL)
        
        # Sanitize HTML
        if self.config.enable_sanitize_html:
            output = self.validator._sanitize_html(output)
        
        # Remove potentially dangerous content
        output = re.sub(r'javascript:', '', output, flags=re.IGNORECASE)
        output = re.sub(r'eval\s*\(', '', output, flags=re.IGNORECASE)
        output = re.sub(r'exec\s*\(', '', output, flags=re.IGNORECASE)
        
        return output.strip()
    
    def generate_api_key(self) -> str:
        """Generate a secure API key."""
        api_key = secrets.token_urlsafe(32)
        self._api_keys.add(api_key)
        return api_key
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        return api_key in self._api_keys
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key."""
        return self._api_keys.discard(api_key)
    
    def generate_session_token(self, user_id: str) -> str:
        """Generate a secure session token."""
        token = secrets.token_urlsafe(32)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        if self._use_redis:
            # Store in Redis with expiration
            try:
                self._redis_client.setex(
                    f"session:{token}",
                    timedelta(hours=24),
                    json.dumps(session_data)
                )
                logger.info(f"Session token stored in Redis for user: {user_id}")
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")
                # Fallback to local storage
                self._session_tokens[token] = session_data
        else:
            # Store in local memory
            self._session_tokens[token] = session_data
        
        return token
    
    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token."""
        if self._use_redis:
            # Try to get from Redis
            try:
                session_data = self._redis_client.get(f"session:{token}")
                if session_data:
                    session_info = json.loads(session_data)
                    # Check expiration
                    expires_at = datetime.fromisoformat(session_info["expires_at"])
                    if datetime.now() < expires_at:
                        return session_info
                    else:
                        # Token expired, remove from Redis
                        self._redis_client.delete(f"session:{token}")
                        logger.info(f"Expired session token removed from Redis: {token}")
                return None
            except Exception as e:
                logger.error(f"Failed to validate session from Redis: {e}")
                # Fallback to local storage
                return self._validate_session_token_local(token)
        else:
            # Use local storage
            return self._validate_session_token_local(token)
    
    def _validate_session_token_local(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token from local storage."""
        session_info = self._session_tokens.get(token)
        if session_info:
            if datetime.now() < datetime.fromisoformat(session_info["expires_at"]):
                return session_info
            else:
                del self._session_tokens[token]
        return None
    
    def cleanup_expired_sessions(self):
        """Clean up expired session tokens."""
        if self._use_redis:
            # Redis handles expiration automatically, but we can log cleanup
            try:
                # Get all session keys and check for expired ones
                session_keys = self._redis_client.keys("session:*")
                now = datetime.now()
                expired_count = 0
                
                for key in session_keys:
                    try:
                        session_data = self._redis_client.get(key)
                        if session_data:
                            session_info = json.loads(session_data)
                            expires_at = datetime.fromisoformat(session_info["expires_at"])
                            if now >= expires_at:
                                self._redis_client.delete(key)
                                expired_count += 1
                    except Exception as e:
                        logger.warning(f"Error checking session {key}: {e}")
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired session tokens from Redis")
            except Exception as e:
                logger.error(f"Failed to cleanup Redis sessions: {e}")
        else:
            # Clean up local sessions
            now = datetime.now()
            expired_tokens = [
                token for token, info in self._session_tokens.items()
                if now >= datetime.fromisoformat(info["expires_at"])
            ]
            
            for token in expired_tokens:
                del self._session_tokens[token]
            
            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired session tokens")
        
        def check_rate_limit(self, identifier: str) -> Dict[str, Any]:
            """
            Check if the identifier (IP/user) has exceeded rate limits.
            Uses Token Bucket algorithm for rate limiting.
            
            Args:
                identifier: IP address or user identifier
                
            Returns:
                Dict with rate limit status and remaining requests
            """
            if not self.config.enable_rate_limiting:
                return {"allowed": True, "remaining": self.rate_limit_max_requests}
            
            current_time = datetime.now()
            window_start = current_time.replace(second=0, microsecond=0)
            
            if self._use_redis:
                return self._check_rate_limit_redis(identifier, current_time)
            else:
                return self._check_rate_limit_local(identifier, current_time, window_start)
        
        def _check_rate_limit_redis(self, identifier: str, current_time: datetime) -> Dict[str, Any]:
            """Check rate limit using Redis for distributed systems."""
            try:
                rate_key = f"rate_limit:{identifier}"
                window_key = f"rate_limit_window:{identifier}"
                
                # Get current request count
                current_count = self._redis_client.get(rate_key)
                current_count = int(current_count) if current_count else 0
                
                # Check if we're in a new window
                window_start = current_time.replace(second=0, microsecond=0)
                window_start_str = window_start.isoformat()
                
                stored_window = self._redis_client.get(window_key)
                
                if stored_window != window_start_str:
                    # New window, reset counter
                    pipe = self._redis_client.pipeline()
                    pipe.set(rate_key, "1")
                    pipe.setex(window_key, self.rate_limit_window, window_start_str)
                    pipe.execute()
                    return {"allowed": True, "remaining": self.rate_limit_max_requests - 1}
                else:
                    # Same window, increment counter
                    if current_count < self.rate_limit_max_requests:
                        self._redis_client.incr(rate_key)
                        remaining = self.rate_limit_max_requests - current_count - 1
                        return {"allowed": True, "remaining": remaining}
                    else:
                        return {"allowed": False, "remaining": 0, "retry_after": self.rate_limit_window}
                        
            except Exception as e:
                logger.error(f"Rate limiting with Redis failed: {e}")
                # Fallback to local rate limiting
                return self._check_rate_limit_local(identifier, current_time, current_time.replace(second=0, microsecond=0))
        
        def _check_rate_limit_local(self, identifier: str, current_time: datetime, window_start: datetime) -> Dict[str, Any]:
            """Check rate limit using local storage for single-server systems."""
            rate_key = f"rate_limit:{identifier}"
            
            # Check if we have existing rate limit data
            if rate_key in self._rate_limits:
                rate_data = self._rate_limits[rate_key]
                
                # Check if we're in a new window
                if rate_data["window_start"] != window_start:
                    # New window, reset counter
                    self._rate_limits[rate_key] = {
                        "count": 1,
                        "window_start": window_start
                    }
                    return {"allowed": True, "remaining": self.rate_limit_max_requests - 1}
                else:
                    # Same window, increment counter
                    if rate_data["count"] < self.rate_limit_max_requests:
                        self._rate_limits[rate_key]["count"] += 1
                        remaining = self.rate_limit_max_requests - rate_data["count"]
                        return {"allowed": True, "remaining": remaining}
                    else:
                        return {"allowed": False, "remaining": 0, "retry_after": self.rate_limit_window}
            else:
                # First request for this identifier
                self._rate_limits[rate_key] = {
                    "count": 1,
                    "window_start": window_start
                }
                return {"allowed": True, "remaining": self.rate_limit_max_requests - 1}
        
        def reset_rate_limit(self, identifier: str) -> bool:
            """Reset rate limit for a specific identifier."""
            if self._use_redis:
                try:
                    self._redis_client.delete(f"rate_limit:{identifier}")
                    self._redis_client.delete(f"rate_limit_window:{identifier}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to reset Redis rate limit: {e}")
                    return False
            else:
                rate_key = f"rate_limit:{identifier}"
                if rate_key in self._rate_limits:
                    del self._rate_limits[rate_key]
                    return True
            return False
        
        def cleanup_rate_limits(self):
            """Clean up expired rate limit entries."""
            if self._use_redis:
                try:
                    # Redis handles TTL automatically for window keys
                    # Just log cleanup status
                    logger.info("Redis rate limits cleanup handled automatically by TTL")
                except Exception as e:
                    logger.error(f"Failed to cleanup Redis rate limits: {e}")
            else:
                # Clean up local rate limits that are older than the window
                current_time = datetime.now()
                expired_keys = []
                
                for key, data in self._rate_limits.items():
                    if current_time - data["window_start"] > timedelta(seconds=self.rate_limit_window):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._rate_limits[key]
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired rate limit entries")
    
    
    # Global security manager instance
default_security_manager = SecurityManager()

# Default security configuration
default_security_config = SecurityConfig(
    level=SecurityLevel.STANDARD,
    max_input_length=10000,
    enable_sanitize_html=True,
    enable_sanitize_urls=True,
    enable_sanitize_json=True,
    detect_prompt_injection=True,
    detect_sql_injection=True,
    detect_xss=True
)

# Global security manager with default configuration
security_manager = SecurityManager(default_security_config)