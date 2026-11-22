"""
Intent Classification Engine for the Universal Intelligence Layer (Phase 03 & Phase 05).
"""

import re
from typing import List, Optional, Set, Tuple
from backend.app.intelligence.schemas import IntentResult, TaskIntent


class IntentClassifier:
    """
    Fast, deterministic, pattern-based and heuristic intent recognition engine.
    Identifies task domain, complexity, required capabilities, suggested tools,
    and action execution requirements.
    """

    # Keyword and regex pattern definitions
    DEBUG_PATTERNS = [
        r"\b(?:error|exception|traceback|stacktrace|bug|crash|fail|failed|broken|syntaxerror|typeerror|valueerror|nullpointer)\b",
        r"\b(?:fix|solve|debug|troubleshoot|why is this failing|doesn't work|not working)\b",
        r"Traceback \(most recent call last\):",
    ]

    CODING_PATTERNS = [
        r"\b(?:python|typescript|javascript|rust|golang|c\+\+|java|sql|html|css|react|fastapi|docker|git|api)\b",
        r"\b(?:function|class|method|component|endpoint|refactor|implement|code|script|algorithm|regex)\b",
        r"```[a-zA-Z]*\n[\s\S]*?```",  # Markdown code blocks
    ]

    MATH_PATTERNS = [
        r"\b(?:calculate|compute|solve for|integral|derivative|matrix|equation|probability|theorem|polynomial|arithmetic)\b",
        r"\b(?:\d+[\+\-\*\/]\d+|\bmath\b|\balgebra\b|\bgeometry\b|\bcalculus\b|\bsqrt\b|\bpercentage\b|\b%\s+of\b)\b",
    ]

    REASONING_PATTERNS = [
        r"\b(?:why|how come|analyze|compare|contrast|trade-?offs|pros and cons|evaluate|critique|deduce|infer)\b",
        r"\b(?:difference between|which is better|architectural review|implications of)\b",
    ]

    RESEARCH_PATTERNS = [
        r"\b(?:research|history of|overview of|literature|explain the concept of|what is|background on|investigate)\b",
        r"\b(?:summarize the key points|state of the art|cite|references|look up|search for)\b",
    ]

    WRITING_PATTERNS = [
        r"\b(?:write|draft|compose|proofread|edit|rephrase|rewrite|polish)\b.*?\b(?:email|letter|post|essay|article|memo|speech|document)\b",
        r"\b(?:draft|write an email|write a letter|proofread|edit this|rephrase|rewrite|polish|tone|essay|article|cover letter)\b",
        r"\b(?:blog post|announcement|newsletter|memo|press release|email to|letter to)\b",
    ]

    CREATIVE_PATTERNS = [
        r"\b(?:creative|brainstorm|story|poem|lyrics|plot|concept|fiction|character|metaphor|dialogue for)\b",
        r"\b(?:imagine|novel ideas|catchy title|slogan)\b",
    ]

    PRODUCTIVITY_PATTERNS = [
        r"\b(?:schedule|plan|agenda|todo|checklist|milestone|roadmap|prioritize|timeline|organize my)\b",
        r"\b(?:meeting notes|action items|daily briefing|routine)\b",
    ]

    DOCUMENT_PATTERNS = [
        r"\b(?:read file|open file|view file|inspect file|list files|find file|directory structure|workspace file)\b",
        r"\b(?:create file|write file|save to file|edit file|update file|delete file|append to file)\b",
    ]

    DATA_ANALYSIS_PATTERNS = [
        r"\b(?:data analysis|analyze dataset|csv|statistics|mean|median|mode|correlation|aggregat|distribution)\b",
    ]

    PLANNING_PATTERNS = [
        r"\b(?:step-by-step plan|break down this task|workflow|execution plan|milestones|phases of implementation)\b",
    ]

    DATETIME_PATTERNS = [
        r"\b(?:what time is it|current time|today's date|current date|what day is it|days until|time in)\b",
        r"\b(?:timezone|time difference|add days|subtract days|epoch time|iso timestamp)\b",
    ]

    @classmethod
    def classify(cls, message: str) -> IntentResult:
        """
        Classifies user prompt into a recognized TaskIntent with parameter recommendations,
        action requirements, and suggested tools.
        """
        text = message.strip()
        lower_text = text.lower()

        # Check for ambiguity (very short ambiguous commands)
        is_ambiguous = False
        clarification_prompt = None
        words = lower_text.split()
        if len(words) <= 2:
            ambiguous_triggers = {"calculate", "compute", "search", "find", "create file", "write", "plan", "debug", "run", "do it", "fix"}
            if lower_text in ambiguous_triggers or (len(words) == 1 and words[0] in ambiguous_triggers):
                is_ambiguous = True
                clarification_prompt = f"Could you provide more details about what you would like to {words[0]}?"

        # Score matching across intent categories
        scores: List[Tuple[TaskIntent, int]] = []

        # 1. Debugging
        debug_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.DEBUG_PATTERNS)
        if "traceback" in lower_text or "exception:" in lower_text:
            debug_score += 4
        scores.append((TaskIntent.DEBUGGING, debug_score))

        # 2. Coding
        code_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.CODING_PATTERNS)
        if "```" in text:
            code_score += 3
        scores.append((TaskIntent.CODING, code_score))

        # 3. Mathematical
        math_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.MATH_PATTERNS)
        scores.append((TaskIntent.MATHEMATICAL, math_score))

        # 4. Reasoning
        reasoning_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.REASONING_PATTERNS)
        scores.append((TaskIntent.REASONING, reasoning_score))

        # 5. Research
        research_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.RESEARCH_PATTERNS)
        scores.append((TaskIntent.RESEARCH, research_score))

        # 6. Writing
        writing_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.WRITING_PATTERNS)
        scores.append((TaskIntent.WRITING, writing_score))

        # 7. Creative
        creative_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.CREATIVE_PATTERNS)
        scores.append((TaskIntent.CREATIVE, creative_score))

        # 8. Productivity
        prod_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.PRODUCTIVITY_PATTERNS)
        scores.append((TaskIntent.PRODUCTIVITY, prod_score))

        # 9. Document Assistance
        doc_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.DOCUMENT_PATTERNS)
        scores.append((TaskIntent.DOCUMENT_ASSISTANCE, doc_score))

        # 10. Data Analysis
        data_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.DATA_ANALYSIS_PATTERNS)
        scores.append((TaskIntent.DATA_ANALYSIS, data_score))

        # 11. Planning
        planning_score = sum(len(re.findall(p, lower_text, re.IGNORECASE)) for p in cls.PLANNING_PATTERNS)
        scores.append((TaskIntent.PLANNING, planning_score))

        # Sort by highest score
        scores.sort(key=lambda x: x[1], reverse=True)
        top_intent, top_score = scores[0]

        # Multi-step detection: if 2 or more distinct strong intents have high scores
        strong_intents = [intent for intent, score in scores if score >= 2]
        if len(strong_intents) >= 2 and any(k in lower_text for k in ["and then", "first", "after that", "also", "step 1"]):
            top_intent = TaskIntent.MULTI_STEP

        # If zero signal, default to GENERAL
        if top_score == 0:
            top_intent = TaskIntent.GENERAL
            confidence = 0.7
        else:
            confidence = min(0.95, 0.6 + (top_score * 0.1))

        # Determine coding and reasoning requirements
        requires_coding = top_intent in [TaskIntent.CODING, TaskIntent.DEBUGGING]
        requires_reasoning = top_intent in [
            TaskIntent.REASONING,
            TaskIntent.MATHEMATICAL,
            TaskIntent.DEBUGGING,
            TaskIntent.CODING,
            TaskIntent.DATA_ANALYSIS,
            TaskIntent.PLANNING,
            TaskIntent.MULTI_STEP,
        ]

        # Detect capabilities and suggested tools
        capabilities: List[str] = []
        suggested_tools: List[str] = []
        requires_action = False

        # Math capability & calculator tool
        has_explicit_math = bool(re.search(r"\b(?:calculate|compute|solve|\d+[\+\-\*\/%]\d+)\b", lower_text))
        if (top_intent == TaskIntent.MATHEMATICAL or has_explicit_math) and any(c in lower_text for c in "+-*/%0123456789"):
            capabilities.append("math")
            suggested_tools.append("calculator")
            requires_action = True

        # Date & time capability
        if any(re.search(p, lower_text, re.IGNORECASE) for p in cls.DATETIME_PATTERNS):
            capabilities.append("datetime")
            suggested_tools.append("datetime_tool")
            requires_action = True

        # File workspace tools
        if re.search(r"\b(?:list|show|display)\s+(?:all\s+)?files\b|\b(?:directory tree|ls)\b", lower_text):
            capabilities.append("file_inspection")
            suggested_tools.append("workspace_list_files")
            requires_action = True
        if re.search(r"\b(?:read|open|view|inspect)\s+(?:a\s+|the\s+)?file\b|\bcat\s+[^\s]+", lower_text):
            capabilities.append("file_read")
            suggested_tools.append("workspace_read_file")
            requires_action = True
        if re.search(r"\b(?:create|write|make|save to)\s+(?:a\s+|the\s+)?file\b", lower_text):
            capabilities.append("file_write")
            suggested_tools.append("workspace_create_file")
            requires_action = True
        if re.search(r"\b(?:edit|update|modify|replace in)\s+(?:a\s+|the\s+)?file\b", lower_text):
            capabilities.append("file_edit")
            suggested_tools.append("workspace_edit_file")
            requires_action = True
        if re.search(r"\b(?:search|find in|grep)\s+(?:all\s+)?files\b|\bsearch code\b", lower_text):
            capabilities.append("file_search")
            suggested_tools.append("workspace_search_files")
            requires_action = True

        # Code tools
        if any(w in lower_text for w in ["search symbols", "find function", "find class"]):
            capabilities.append("code_symbol_search")
            suggested_tools.append("code_search_symbols")
            requires_action = True
        if any(w in lower_text for w in ["inspect codebase", "code structure", "analyze structure"]):
            capabilities.append("code_inspection")
            suggested_tools.append("code_inspect_structure")
            requires_action = True
        if any(w in lower_text for w in ["propose changes", "generate diff", "show patch"]):
            capabilities.append("code_diff")
            suggested_tools.append("code_propose_changes")
            requires_action = True
        if any(w in lower_text for w in ["apply patch", "apply changes to"]):
            capabilities.append("code_patch")
            suggested_tools.append("code_apply_patch")
            requires_action = True

        # Web / Research search
        if any(w in lower_text for w in ["search the web", "search online", "research online", "latest info on", "look up online"]):
            capabilities.append("web_search")
            suggested_tools.append("research_search")
            requires_action = True

        # Pure conversational exclusion: greetings, general questions don't require action
        conversational_phrases = {"hi", "hello", "hey", "how are you", "who are you", "what can you do", "help"}
        if lower_text in conversational_phrases or (len(words) <= 3 and any(w in conversational_phrases for w in words)):
            requires_action = False
            suggested_tools.clear()

        # Recommended temperatures
        temp_map = {
            TaskIntent.DEBUGGING: 0.2,
            TaskIntent.MATHEMATICAL: 0.2,
            TaskIntent.CODING: 0.3,
            TaskIntent.DATA_ANALYSIS: 0.3,
            TaskIntent.PLANNING: 0.4,
            TaskIntent.MULTI_STEP: 0.4,
            TaskIntent.REASONING: 0.5,
            TaskIntent.RESEARCH: 0.6,
            TaskIntent.PRODUCTIVITY: 0.5,
            TaskIntent.DOCUMENT_ASSISTANCE: 0.5,
            TaskIntent.GENERAL: 0.7,
            TaskIntent.WRITING: 0.75,
            TaskIntent.CREATIVE: 0.85,
        }
        suggested_temp = temp_map.get(top_intent, 0.7)

        return IntentResult(
            intent=top_intent,
            confidence=round(confidence, 2),
            requires_coding=requires_coding,
            requires_reasoning=requires_reasoning,
            requires_action=requires_action,
            suggested_temperature=suggested_temp,
            summary=f"Identified intent: {top_intent.value} (confidence: {round(confidence, 2)})",
            detected_capabilities=capabilities,
            suggested_tools=suggested_tools,
            is_ambiguous=is_ambiguous,
            clarification_prompt=clarification_prompt,
        )
