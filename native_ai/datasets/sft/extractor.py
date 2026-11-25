"""SFT Data Extraction and Tree Reconstruction Module for LOVE Native AI (NAI-07A).

Extracts and normalizes multi-turn conversations from approved sources:
1. OpenAssistant OASST1 (Apache-2.0, English, review-verified, tree-structured)
2. GSM8K (MIT, multi-step mathematical reasoning)
3. LOVE Curated Seed Corpus (CC0-1.0, structured extraction, system tasks)

Applies:
- Tree reconstruction: builds complete conversation branches from root prompt to leaf assistant turn.
- Quality filtering: removes deleted, unreviewed, toxic, spam, or PII-flagged messages.
- Role normalization: maps upstream roles ('prompter', 'assistant') to standard LOVE roles ('user', 'assistant').
- Category attribution across 6 core capabilities:
  - general_conversation
  - instruction_following
  - writing_summarization
  - reasoning_mathematics
  - structured_output
  - safe_refusal
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

import pyarrow.parquet as pq

from native_ai.datasets.sft.format import Message, ConversationExample, LOVEInstructionFormatter


def categorize_conversation(messages: List[Message], default_cat: str = "general_conversation") -> str:
    """
    Categorizes conversation into standard LOVE SFT capability categories based on prompt semantics:
    - reasoning_mathematics: math, equations, logic puzzles, arithmetic
    - structured_output: JSON, YAML, tables, schema extraction, formatting
    - writing_summarization: essays, summarization, creative writing, correspondence, paraphrasing
    - safe_refusal: safety boundaries, ethical refusals, harmful instruction rejection
    - instruction_following: procedural commands, explicit constraints, technical instructions
    - general_conversation: open-ended chat, general knowledge Q&A, greetings
    """
    if not messages:
        return default_cat

    # Analyze first user prompt and first assistant response
    user_text = ""
    asst_text = ""
    for m in messages:
        if m.role == "user" and not user_text:
            user_text = m.content.lower()
        elif m.role == "assistant" and not asst_text:
            asst_text = m.content.lower()

    combined = f"{user_text} {asst_text}"

    # 1. Safe Refusal / Boundary
    refusal_patterns = [
        r"\bi cannot\b", r"\bi am unable to\b", r"\bas an ai\b", r"\billegal\b",
        r"\bunethical\b", r"\bharmful\b", r"\bdangerous\b", r"\bi must refuse\b",
        r"\bi'm sorry, but\b", r"\bviolates safety\b"
    ]
    if any(re.search(p, asst_text) for p in refusal_patterns):
        return "safe_refusal"

    # 2. Structured Output
    structured_patterns = [
        r"\bjson\b", r"\byaml\b", r"\btable\b", r"\bmarkdown table\b", r"\bcsv\b",
        r"\bformat as\b", r"\bextract the following\b", r"\bschema\b", r"\bstructured output\b",
        r"```json", r"```yaml", r"```csv"
    ]
    if any(re.search(p, user_text) for p in structured_patterns):
        return "structured_output"

    # 3. Reasoning & Mathematics
    math_patterns = [
        r"\bcalculate\b", r"\bsolve\b", r"\bequation\b", r"\bmath\b", r"\balgebra\b",
        r"\bprobability\b", r"\barithmetic\b", r"\btheorem\b", r"\bproof\b",
        r"\bhow many\b", r"\bcompute\b", r"\bderivative\b", r"\bintegral\b"
    ]
    if any(re.search(p, user_text) for p in math_patterns):
        return "reasoning_mathematics"

    # 4. Writing & Summarization
    writing_patterns = [
        r"\bsummarize\b", r"\bsummary\b", r"\bwrite an essay\b", r"\bwrite a story\b",
        r"\bpoem\b", r"\bparaphrase\b", r"\bdraft an email\b", r"\brewrite\b",
        r"\bbullet points\b", r"\btldr\b", r"\bcreative writing\b"
    ]
    if any(re.search(p, user_text) for p in writing_patterns):
        return "writing_summarization"

    # 5. Instruction Following
    instruction_patterns = [
        r"\bexplain\b", r"\bstep-by-step\b", r"\bhow do i\b", r"\bhow to\b",
        r"\bcompare and contrast\b", r"\blist\b", r"\bguide\b", r"\binstructions\b"
    ]
    if any(re.search(p, user_text) for p in instruction_patterns):
        return "instruction_following"

    return default_cat


class SFTDataExtractor:
    """Extracts raw instruction examples from approved local sources."""

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir

    def extract_oasst1(
        self,
        max_branches_per_tree: int = 3,
    ) -> Tuple[List[ConversationExample], Dict[str, Any]]:
        """
        Extracts conversations from OpenAssistant OASST1 parquet files.
        Preserves tree grouping so related branches stay in the same split.
        Limits branches per tree to prevent oversampling the same root prompt.
        """
        oasst_dir = self.raw_dir / "external" / "oasst1"
        files = [oasst_dir / "train.parquet", oasst_dir / "validation.parquet"]

        stats = {
            "source": "OpenAssistant/oasst1",
            "license": "Apache-2.0",
            "raw_messages": 0,
            "english_messages": 0,
            "deleted_rejected": 0,
            "review_rejected": 0,
            "toxicity_spam_rejected": 0,
            "retained_messages": 0,
            "unique_trees": 0,
            "admitted_conversations": 0,
            "single_turn_conversations": 0,
            "multi_turn_conversations": 0,
        }

        all_rows = []
        for fp in files:
            if fp.exists():
                table = pq.read_table(fp)
                stats["raw_messages"] += table.num_rows
                all_rows.extend(table.to_pylist())

        # Filter clean English messages
        clean_rows = []
        for r in all_rows:
            if r.get("lang") != "en":
                continue
            stats["english_messages"] += 1

            if r.get("deleted", False):
                stats["deleted_rejected"] += 1
                continue

            if r.get("review_result") is not True:
                stats["review_rejected"] += 1
                continue

            # Quality and Toxicity checks
            labels = r.get("labels") or {}
            ldict = dict(zip(labels.get("name") or [], labels.get("value") or []))
            detox = r.get("detoxify") or {}

            is_bad = (
                ldict.get("spam", 0.0) > 0.5
                or ldict.get("not_appropriate", 0.0) > 0.5
                or ldict.get("pii", 0.0) > 0.5
                or ldict.get("hate_speech", 0.0) > 0.5
                or detox.get("toxicity", 0.0) > 0.5
                or detox.get("severe_toxicity", 0.0) > 0.5
            )
            if is_bad:
                stats["toxicity_spam_rejected"] += 1
                continue

            clean_rows.append(r)

        stats["retained_messages"] = len(clean_rows)

        # Group by message_tree_id
        tree_msgs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in clean_rows:
            tree_msgs[r["message_tree_id"]].append(r)

        stats["unique_trees"] = len(tree_msgs)
        conversations: List[ConversationExample] = []

        for tree_id, msgs in tree_msgs.items():
            tree_dict = {m["message_id"]: m for m in msgs}
            children: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            roots: List[Dict[str, Any]] = []

            for m in msgs:
                pid = m.get("parent_id")
                if pid is None or pid not in tree_dict:
                    roots.append(m)
                else:
                    children[pid].append(m)

            def get_paths(node: Dict[str, Any], curr_path: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
                path = curr_path + [node]
                c_list = children.get(node["message_id"], [])
                if not c_list:
                    return [path]
                res = []
                for c in c_list:
                    res.extend(get_paths(c, path))
                return res

            tree_paths = []
            for r in roots:
                tree_paths.extend(get_paths(r, []))

            # Filter valid paths: must start with prompter, end with assistant
            valid_paths = []
            for path in tree_paths:
                if len(path) >= 2 and path[0]["role"] == "prompter" and path[-1]["role"] == "assistant":
                    valid_paths.append(path)

            # Limit branches per tree to prevent oversampling
            if len(valid_paths) > max_branches_per_tree:
                # Prefer diverse path depths: shortest, median, longest
                valid_paths.sort(key=len)
                selected_paths = [
                    valid_paths[0],
                    valid_paths[len(valid_paths) // 2],
                    valid_paths[-1],
                ]
            else:
                selected_paths = valid_paths

            for branch_idx, path in enumerate(selected_paths):
                # Verify strict role alternation
                messages: List[Message] = []
                # Add default system message
                messages.append(Message(role="system", content=LOVEInstructionFormatter.DEFAULT_SYSTEM_PROMPT))

                valid_alternation = True
                expected_role = "prompter"
                for m in path:
                    if m["role"] != expected_role:
                        valid_alternation = False
                        break
                    std_role = "user" if m["role"] == "prompter" else "assistant"
                    content = m.get("text", "").strip()
                    if not content:
                        valid_alternation = False
                        break
                    messages.append(Message(role=std_role, content=content))
                    expected_role = "assistant" if expected_role == "prompter" else "prompter"

                if not valid_alternation or len(messages) < 3:
                    continue

                category = categorize_conversation(messages, default_cat="general_conversation")
                conv_id = f"oasst1_{tree_id[:8]}_b{branch_idx:02d}"

                example = ConversationExample(
                    conversation_id=conv_id,
                    tree_id=f"oasst_tree_{tree_id}",
                    source_id="src_ext_oasst1",
                    category=category,
                    license="Apache-2.0",
                    messages=messages,
                    quality_score=1.0,
                    metadata={
                        "upstream_tree_id": tree_id,
                        "leaf_msg_id": path[-1]["message_id"],
                        "turn_count": (len(messages) - 1) // 2,
                    },
                )
                conversations.append(example)
                stats["admitted_conversations"] += 1
                if len(messages) == 3:
                    stats["single_turn_conversations"] += 1
                else:
                    stats["multi_turn_conversations"] += 1

        return conversations, stats

    def extract_gsm8k(self) -> Tuple[List[ConversationExample], Dict[str, Any]]:
        """
        Extracts mathematical word problems from GSM8K train split.
        Formats each as a clean single-turn instruction-response pair.
        """
        gsm_path = self.raw_dir / "external" / "gsm8k" / "train.parquet"
        stats = {
            "source": "openai/gsm8k",
            "license": "MIT",
            "raw_problems": 0,
            "admitted_conversations": 0,
        }

        if not gsm_path.exists():
            return [], stats

        table = pq.read_table(gsm_path)
        stats["raw_problems"] = table.num_rows
        rows = table.to_pylist()

        conversations: List[ConversationExample] = []
        for i, r in enumerate(rows):
            q = r.get("question", "").strip()
            a = r.get("answer", "").strip()
            if not q or not a:
                continue

            # Format clean user prompt and step-by-step reasoning answer
            user_content = f"Solve the following math word problem step-by-step:\n\n{q}"
            asst_content = f"Step-by-step Solution:\n{a}"

            conv_id = f"gsm8k_train_{i:05d}"
            tree_id = f"gsm8k_prob_{i:05d}"

            messages = [
                Message(role="system", content="You are LOVE, an intelligent assistant focused on precision and mathematical reasoning."),
                Message(role="user", content=user_content),
                Message(role="assistant", content=asst_content),
            ]

            example = ConversationExample(
                conversation_id=conv_id,
                tree_id=tree_id,
                source_id="src_ext_gsm8k",
                category="reasoning_mathematics",
                license="MIT",
                messages=messages,
                quality_score=1.0,
                metadata={"problem_index": i},
            )
            conversations.append(example)
            stats["admitted_conversations"] += 1

        return conversations, stats

    def extract_seed_tasks(self) -> Tuple[List[ConversationExample], Dict[str, Any]]:
        """
        Extracts high-quality synthetic task fixtures from curated seed files:
        - instruction_dialog.jsonl
        - structured_tasks.jsonl
        - reasoning_math.jsonl
        - technical_code.jsonl
        Deduplicates identical records.
        """
        import json
        from native_ai.datasets.privacy_filter import PrivacyFilter

        privacy_filter = PrivacyFilter()
        stats = {
            "source": "LOVE Native AI Seed Corpus",
            "license": "CC0-1.0",
            "raw_records": 0,
            "deduplicated_records": 0,
            "privacy_rejected": 0,
            "admitted_conversations": 0,
        }

        conversations: List[ConversationExample] = []
        seen_texts: Set[str] = set()

        # 1. Parse instruction_dialog.jsonl
        dialog_path = self.raw_dir / "instruction_dialog.jsonl"
        if dialog_path.exists():
            with open(dialog_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    stats["raw_records"] += 1
                    rec = json.loads(line)
                    raw_text = rec.get("text", "").strip()
                    doc_id = rec.get("doc_id", "seed_dialog")

                    if raw_text in seen_texts:
                        continue
                    seen_texts.add(raw_text)
                    stats["deduplicated_records"] += 1

                    is_admitted, clean_text, _ = privacy_filter.inspect_and_filter(raw_text)
                    if not is_admitted:
                        stats["privacy_rejected"] += 1
                        continue

                    # Robust tag parsing
                    splits = re.split(r"(<\|system\|>|<\|user\|>|<\|assistant\|>)", clean_text)
                    parsed_msgs: List[Message] = []
                    current_role = None
                    for part in splits:
                        part = part.strip()
                        if not part:
                            continue
                        if part in ("<|system|>", "<|user|>", "<|assistant|>"):
                            current_role = part[2:-2]
                        elif current_role is not None:
                            parsed_msgs.append(Message(role=current_role, content=part))
                            current_role = None

                    if len(parsed_msgs) >= 2 and parsed_msgs[-1].role == "assistant":
                        cat = categorize_conversation(parsed_msgs, default_cat="instruction_following")
                        conversations.append(ConversationExample(
                            conversation_id=f"seed_{doc_id}",
                            tree_id=f"seed_tree_{doc_id}",
                            source_id="src_seed_dialog",
                            category=cat,
                            license="CC0-1.0",
                            messages=parsed_msgs,
                            quality_score=1.0,
                            metadata={"doc_id": doc_id},
                        ))
                        stats["admitted_conversations"] += 1

        # 2. Parse structured_tasks.jsonl
        struct_path = self.raw_dir / "structured_tasks.jsonl"
        if struct_path.exists():
            with open(struct_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    stats["raw_records"] += 1
                    rec = json.loads(line)
                    raw_text = rec.get("text", "").strip()
                    doc_id = rec.get("doc_id", "seed_struct")

                    if raw_text in seen_texts:
                        continue
                    seen_texts.add(raw_text)
                    stats["deduplicated_records"] += 1

                    is_admitted, clean_text, _ = privacy_filter.inspect_and_filter(raw_text)
                    if not is_admitted:
                        stats["privacy_rejected"] += 1
                        continue

                    # Split by Output
                    match = re.search(r"(Output (?:JSON|Execution Plan):.*)", clean_text, re.DOTALL)
                    if match:
                        user_part = clean_text[:match.start()].strip()
                        asst_part = match.group(1).strip()
                        msgs = [
                            Message(role="system", content="You are LOVE, an intelligent assistant focused on precision and structured data."),
                            Message(role="user", content=user_part),
                            Message(role="assistant", content=asst_part),
                        ]
                        conversations.append(ConversationExample(
                            conversation_id=f"seed_{doc_id}",
                            tree_id=f"seed_tree_{doc_id}",
                            source_id="src_seed_struct",
                            category="structured_output",
                            license="CC0-1.0",
                            messages=msgs,
                            quality_score=1.0,
                            metadata={"doc_id": doc_id},
                        ))
                        stats["admitted_conversations"] += 1

        # 3. Parse reasoning_math.jsonl
        math_path = self.raw_dir / "reasoning_math.jsonl"
        if math_path.exists():
            with open(math_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    stats["raw_records"] += 1
                    rec = json.loads(line)
                    raw_text = rec.get("text", "").strip()
                    doc_id = rec.get("doc_id", "seed_math")

                    if raw_text in seen_texts:
                        continue
                    seen_texts.add(raw_text)
                    stats["deduplicated_records"] += 1

                    is_admitted, clean_text, _ = privacy_filter.inspect_and_filter(raw_text)
                    if not is_admitted:
                        stats["privacy_rejected"] += 1
                        continue

                    # Find problem vs solution
                    # Header usually '# Mathematical Reasoning: ...\n\nProblem: ...\n\nStep 1: ...'
                    if "Problem:" in clean_text and ("Step 1:" in clean_text or "Proof" in clean_text or "1." in clean_text):
                        parts = re.split(r"(Step 1:|Proof by Contradiction:|To derive the quadratic formula|Bayes' Rule states)", clean_text, maxsplit=1)
                        if len(parts) >= 3:
                            user_part = parts[0].strip()
                            asst_part = (parts[1] + parts[2]).strip()
                        else:
                            user_part = "Solve the following problem step-by-step:"
                            asst_part = clean_text.strip()
                    else:
                        user_part = "Please provide the mathematical derivation and proof:"
                        asst_part = clean_text.strip()

                    msgs = [
                        Message(role="system", content="You are LOVE, an intelligent assistant focused on mathematical reasoning and rigor."),
                        Message(role="user", content=user_part),
                        Message(role="assistant", content=asst_part),
                    ]
                    conversations.append(ConversationExample(
                        conversation_id=f"seed_{doc_id}",
                        tree_id=f"seed_tree_{doc_id}",
                        source_id="src_seed_math",
                        category="reasoning_mathematics",
                        license="CC0-1.0",
                        messages=msgs,
                        quality_score=1.0,
                        metadata={"doc_id": doc_id},
                    ))
                    stats["admitted_conversations"] += 1

        # 4. Parse technical_code.jsonl
        code_path = self.raw_dir / "technical_code.jsonl"
        if code_path.exists():
            with open(code_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    stats["raw_records"] += 1
                    rec = json.loads(line)
                    raw_text = rec.get("text", "").strip()
                    doc_id = rec.get("doc_id", "seed_code")

                    if raw_text in seen_texts:
                        continue
                    seen_texts.add(raw_text)
                    stats["deduplicated_records"] += 1

                    # Privacy filter strictly checks for secrets (e.g. RSA private keys)
                    is_admitted, clean_text, flags = privacy_filter.inspect_and_filter(raw_text)
                    if not is_admitted:
                        stats["privacy_rejected"] += 1
                        continue

                    # Header line as prompt, remainder as assistant response
                    lines = clean_text.splitlines()
                    title = lines[0].lstrip("#").strip() if lines else "Technical code question"
                    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else clean_text

                    user_part = f"Can you explain and provide an implementation for: {title}?"
                    asst_part = body

                    msgs = [
                        Message(role="system", content="You are LOVE, a technical assistant specialized in software engineering and algorithms."),
                        Message(role="user", content=user_part),
                        Message(role="assistant", content=asst_part),
                    ]
                    conversations.append(ConversationExample(
                        conversation_id=f"seed_{doc_id}",
                        tree_id=f"seed_tree_{doc_id}",
                        source_id="src_seed_code",
                        category="instruction_following",
                        license="CC0-1.0",
                        messages=msgs,
                        quality_score=1.0,
                        metadata={"doc_id": doc_id},
                    ))
                    stats["admitted_conversations"] += 1

        return conversations, stats
