"""Prompt Injection and Security Guardrail module.

Protects against OWASP Top 10 for Large Language Models (LLM01: Prompt Injection,
LLM06: Sensitive Information Disclosure, and LLM07: System Prompt Leakage).
"""

import re
import base64
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from app.core.config import settings


class ThreatCategory(str, Enum):
    """Categorization of detected adversarial threats."""
    CLEAN = "CLEAN"
    DIRECT_INJECTION = "DIRECT_INJECTION"
    JAILBREAK = "JAILBREAK"
    PROMPT_LEAK = "PROMPT_LEAK"
    DELIMITER_HIJACKING = "DELIMITER_HIJACKING"
    ENCODED_PAYLOAD = "ENCODED_PAYLOAD"


@dataclass
class SecurityScanResult:
    """Detailed result of a prompt security scan."""
    is_safe: bool
    risk_score: float  # 0.0 (benign) to 1.0 (malicious)
    threat_category: ThreatCategory
    detected_patterns: List[str] = field(default_factory=list)
    mitigation_action: str = "ALLOW"
    explanation: Optional[str] = None


class PromptGuard:
    """Multi-layered prompt security firewall."""

    # High-confidence direct instruction override patterns
    DIRECT_INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        r"disregard\s+(?:all\s+)?(?:previous|prior|system)\s+(?:rules|directions|prompts)",
        r"forget\s+(?:all\s+)?(?:previous|prior)\s+instructions",
        r"override\s+(?:all\s+)?(?:system|safety|security|\w+\s+and\s+\w+)*\s+instructions",
        r"bypass\s+(?:all\s+)?safety\s+filters",
        r"new\s+system\s+directive",
        r"stop\s+being\s+(?:an?\s+)?ai",
        r"you\s+must\s+now\s+follow\s+these\s+instructions\s+instead",
    ]

    # Jailbreak & Persona evasion patterns (DAN, Developer Mode, etc.)
    JAILBREAK_PATTERNS = [
        r"\bdo\s+anything\s+now\b",
        r"\bDAN\s+mode\b",
        r"\bdeveloper\s+mode\s+enabled\b",
        r"act\s+as\s+an?\s+unrestricted\b",
        r"pretend\s+you\s+have\s+no\s+(?:ethics|rules|constraints|filters)",
        r"you\s+are\s+now\s+(?:evil|unfiltered|jailbroken)",
        r"simulate\s+a\s+conversation\s+where\s+safety\s+is\s+disabled",
        r"in\s+this\s+hypothetical\s+scenario,\s+ignore\s+all\s+guardrails",
    ]

    # Delimiter and prompt markup hijacking patterns
    DELIMITER_PATTERNS = [
        r"<\|(?:im_start|im_end|system|user|assistant)\|>",
        r"\[(?:INST|/INST|SYS|/SYS)\]",
        r"```(?:system|admin|override)",
        r"###\s*(?:System|Instruction|Override):",
        r"Human:\s*.*\s*Assistant:",
    ]

    # System prompt extraction & reconnaissance
    PROMPT_LEAK_PATTERNS = [
        r"(?:print|output|display|show|reveal|repeat)\s+(?:your\s+)?(?:system\s+(?:prompt|instructions)|initial\s+instructions|internal\s+directives)",
        r"what\s+(?:are|were)\s+your\s+(?:original|initial|system)\s+instructions",
        r"verbatim\s+copy\s+of\s+your\s+instructions",
        r"echo\s+back\s+everything\s+above",
    ]

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._compiled_direct = [re.compile(p, re.IGNORECASE) for p in self.DIRECT_INJECTION_PATTERNS]
        self._compiled_jailbreak = [re.compile(p, re.IGNORECASE) for p in self.JAILBREAK_PATTERNS]
        self._compiled_delimiter = [re.compile(p, re.IGNORECASE) for p in self.DELIMITER_PATTERNS]
        self._compiled_leak = [re.compile(p, re.IGNORECASE) for p in self.PROMPT_LEAK_PATTERNS]

    def _check_encoded_payloads(self, text: str) -> Optional[str]:
        """Detect base64 obfuscated attack strings."""
        # Find potential base64 tokens of length >= 24
        b64_candidates = re.findall(r"[A-Za-z0-9+/]{24,}={0,2}", text)
        for token in b64_candidates:
            try:
                decoded = base64.b64decode(token).decode("utf-8", errors="ignore").lower()
                for keyword in ["ignore previous", "system prompt", "bypass", "jailbreak"]:
                    if keyword in decoded:
                        return f"Base64 encoded adversarial instruction: '{keyword}'"
            except Exception:
                continue
        return None

    def scan_query(self, query: str) -> SecurityScanResult:
        """Analyze a user query for adversarial prompt injection signatures."""
        if not self.enabled:
            return SecurityScanResult(
                is_safe=True,
                risk_score=0.0,
                threat_category=ThreatCategory.CLEAN,
                mitigation_action="ALLOW",
                explanation="Security guardrails are disabled.",
            )

        detected_patterns = []

        # 1. Delimiter Hijacking check
        for pattern in self._compiled_delimiter:
            if pattern.search(query):
                detected_patterns.append(f"Delimiter match: {pattern.pattern}")

        if detected_patterns:
            return SecurityScanResult(
                is_safe=False,
                risk_score=0.95,
                threat_category=ThreatCategory.DELIMITER_HIJACKING,
                detected_patterns=detected_patterns,
                mitigation_action="BLOCK",
                explanation="Malicious control token or delimiter injection detected.",
            )

        # 2. Direct Instruction Override check
        for pattern in self._compiled_direct:
            if pattern.search(query):
                detected_patterns.append(f"Direct injection pattern: {pattern.pattern}")

        if detected_patterns:
            return SecurityScanResult(
                is_safe=False,
                risk_score=0.90,
                threat_category=ThreatCategory.DIRECT_INJECTION,
                detected_patterns=detected_patterns,
                mitigation_action="BLOCK",
                explanation="Adversarial instruction override attempt detected.",
            )

        # 3. Jailbreak / Persona Manipulation check
        for pattern in self._compiled_jailbreak:
            if pattern.search(query):
                detected_patterns.append(f"Jailbreak pattern: {pattern.pattern}")

        if detected_patterns:
            return SecurityScanResult(
                is_safe=False,
                risk_score=0.85,
                threat_category=ThreatCategory.JAILBREAK,
                detected_patterns=detected_patterns,
                mitigation_action="BLOCK",
                explanation="Jailbreak or adversarial persona manipulation detected.",
            )

        # 4. System Prompt Extraction check
        for pattern in self._compiled_leak:
            if pattern.search(query):
                detected_patterns.append(f"Prompt leak attempt: {pattern.pattern}")

        if detected_patterns:
            return SecurityScanResult(
                is_safe=False,
                risk_score=0.80,
                threat_category=ThreatCategory.PROMPT_LEAK,
                detected_patterns=detected_patterns,
                mitigation_action="BLOCK",
                explanation="System prompt reconnaissance or exfiltration attempt detected.",
            )

        # 5. Base64 / Obfuscated payload check
        b64_reason = self._check_encoded_payloads(query)
        if b64_reason:
            return SecurityScanResult(
                is_safe=False,
                risk_score=0.88,
                threat_category=ThreatCategory.ENCODED_PAYLOAD,
                detected_patterns=[b64_reason],
                mitigation_action="BLOCK",
                explanation="Obfuscated payload detected in input.",
            )

        # Benign Query
        return SecurityScanResult(
            is_safe=True,
            risk_score=0.05,
            threat_category=ThreatCategory.CLEAN,
            detected_patterns=[],
            mitigation_action="ALLOW",
            explanation="Input passed all security guardrail checks.",
        )

    def scan_output(self, response_text: str, system_prompt: str) -> bool:
        """Output guardrail: verify that generated response doesn't leak secrets or system prompt."""
        if not self.enabled or not settings.output_guard_enabled:
            return True

        # Check for system prompt verbatim leakage
        sys_snippet = system_prompt[:60].strip()
        if sys_snippet and sys_snippet.lower() in response_text.lower():
            return False

        # Check for credential / secret regexes
        secret_patterns = [
            r"bearer\s+[A-Za-z0-9\-_\.=]{20,}",
            r"(?:api[_-]?key|secret|password)\s*[:=]\s*['\"][A-Za-z0-9\-_\.]{16,}['\"]",
            r"azure[_-]?openai[_-]?api[_-]?key",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return False

        return True


# Default instance
security_guard = PromptGuard(enabled=settings.security_enabled)
