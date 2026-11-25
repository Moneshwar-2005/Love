"""LOVE Instruction Format and SFT Tokenization/Masking Specification (NAI-07A).

Defines:
- Versioned message schema for LOVE Supervised Fine-Tuning (SFT v1.0).
- Special token constants matching LoveTokenizer v0.1:
  <pad>: 0, <unk>: 1, <bos>: 2, <eos>: 3, <|system|>: 4, <|user|>: 5, <|assistant|>: 6, <|tool|>: 7
- Causal language modeling target shift and assistant-only loss masking:
  inputs = S[:-1], targets = L[1:]
  where all prompt tokens (system, user, role headers) and padding have target = -100,
  and only assistant response content tokens and concluding <eos> have active target token IDs.
- Truncation safety: prevents silent truncation of assistant responses.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Union

PAD_TOKEN_ID = 0
UNK_TOKEN_ID = 1
BOS_TOKEN_ID = 2
EOS_TOKEN_ID = 3         # <eos> / <|endoftext|>
SYSTEM_TOKEN_ID = 4      # <|system|>
USER_TOKEN_ID = 5        # <|user|>
ASSISTANT_TOKEN_ID = 6   # <|assistant|>
TOOL_TOKEN_ID = 7        # <|tool|>

IGNORE_INDEX = -100      # PyTorch cross_entropy default ignore index


class TruncationSafetyError(ValueError):
    """Raised when a conversation cannot be safely truncated without corrupting prompt context or assistant target."""
    pass


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationExample:
    conversation_id: str
    tree_id: str
    source_id: str
    category: str
    license: str
    messages: List[Message]
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "tree_id": self.tree_id,
            "source_id": self.source_id,
            "category": self.category,
            "license": self.license,
            "messages": [m.to_dict() for m in self.messages],
            "quality_score": self.quality_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationExample":
        return cls(
            conversation_id=data["conversation_id"],
            tree_id=data.get("tree_id", data["conversation_id"]),
            source_id=data["source_id"],
            category=data["category"],
            license=data["license"],
            messages=[Message.from_dict(m) for m in data["messages"]],
            quality_score=data.get("quality_score", 1.0),
            metadata=data.get("metadata", {}),
        )


class LOVEInstructionFormatter:
    """Formatter and tokenizer for LOVE SFT v1.0."""

    FORMAT_VERSION = "1.0.0"
    DEFAULT_SYSTEM_PROMPT = "You are LOVE, a helpful, precise, and concise native AI assistant."

    @staticmethod
    def validate_conversation(example: ConversationExample) -> Tuple[bool, Optional[str]]:
        """
        Validates structural rules of an SFT conversation:
        1. At least 2 messages (must include user and assistant).
        2. System message must be first if present.
        3. First conversational turn must be 'user'.
        4. Last message must be 'assistant'.
        5. Roles must strictly alternate between 'user' and 'assistant'.
        6. Message contents must be non-empty strings.
        """
        msgs = example.messages
        if not msgs or len(msgs) < 2:
            return False, "Conversation must contain at least 2 messages."

        idx = 0
        if msgs[0].role == "system":
            if not msgs[0].content.strip():
                return False, "System message content cannot be empty."
            idx = 1

        conv_turns = msgs[idx:]
        if not conv_turns:
            return False, "Conversation must have user and assistant turns after system message."

        if conv_turns[0].role != "user":
            return False, f"First conversation turn must be 'user', got '{conv_turns[0].role}'."

        if conv_turns[-1].role != "assistant":
            return False, f"Last conversation turn must be 'assistant', got '{conv_turns[-1].role}'."

        expected_role = "user"
        for i, m in enumerate(conv_turns):
            if m.role not in ("user", "assistant"):
                return False, f"Invalid role '{m.role}' at index {idx + i}."
            if m.role != expected_role:
                return False, f"Role ordering violation at index {idx + i}: expected '{expected_role}', got '{m.role}'."
            if not m.content.strip():
                return False, f"Empty content in message {idx + i} ({m.role})."
            expected_role = "assistant" if expected_role == "user" else "user"

        return True, None

    @classmethod
    def serialize_text(cls, example: ConversationExample) -> str:
        """
        Serializes conversation into textual string representation with explicit role markers:
        <|system|>{sys}<eos><|user|>{usr}<eos><|assistant|>{asst}<eos>
        """
        parts = []
        for m in example.messages:
            content = m.content.strip()
            parts.append(f"<|{m.role}|>{content}<eos>")
        return "".join(parts)

    @classmethod
    def encode_conversation(
        cls,
        example: ConversationExample,
        tokenizer: Any,
        max_seq_len: int = 512,
        allow_turn_truncation: bool = True,
    ) -> Tuple[List[int], List[int]]:
        """
        Encodes conversation into shifted causal language modeling pairs (inputs, targets):
        - inputs: tokens [0 : seq_len]
        - targets: tokens [1 : seq_len + 1] with prompt and header positions masked to IGNORE_INDEX (-100).
        - Assistant response content tokens and concluding EOS_TOKEN_ID are active targets.

        Returns (input_ids, target_ids) each of length <= max_seq_len.
        Raises TruncationSafetyError if the target turn cannot fit safely within max_seq_len.
        """
        is_valid, reason = cls.validate_conversation(example)
        if not is_valid:
            raise ValueError(f"Invalid conversation: {reason}")

        # Separate system message and conversation turns
        sys_msg: Optional[Message] = None
        turns: List[Message] = []
        for m in example.messages:
            if m.role == "system":
                sys_msg = m
            else:
                turns.append(m)

        # Build token blocks
        # Each block: (tokens, is_assistant_content)
        def encode_message_block(role: str, content: str) -> Tuple[List[int], List[int]]:
            content_tokens = tokenizer.encode(content.strip())
            if role == "system":
                tokens = [SYSTEM_TOKEN_ID] + content_tokens + [EOS_TOKEN_ID]
                labels = [IGNORE_INDEX] * len(tokens)
            elif role == "user":
                tokens = [USER_TOKEN_ID] + content_tokens + [EOS_TOKEN_ID]
                labels = [IGNORE_INDEX] * len(tokens)
            elif role == "assistant":
                header = [ASSISTANT_TOKEN_ID]
                header_labels = [IGNORE_INDEX]
                eos = [EOS_TOKEN_ID]
                eos_labels = [EOS_TOKEN_ID]
                tokens = header + content_tokens + eos
                labels = header_labels + content_tokens + eos_labels
            else:
                raise ValueError(f"Unsupported role: {role}")
            return tokens, labels

        sys_tokens: List[int] = []
        sys_labels: List[int] = []
        if sys_msg is not None:
            sys_tokens, sys_labels = encode_message_block("system", sys_msg.content)
        else:
            sys_tokens, sys_labels = encode_message_block("system", cls.DEFAULT_SYSTEM_PROMPT)

        # Turn pairs: each turn pair is (user_msg, asst_msg)
        turn_blocks: List[Tuple[List[int], List[int]]] = []
        for m in turns:
            t, l = encode_message_block(m.role, m.content)
            turn_blocks.append((t, l))

        # Check total sequence length (inputs need total_len - 1 <= max_seq_len, so total_len <= max_seq_len + 1)
        req_len = max_seq_len + 1

        def assemble(blocks: List[Tuple[List[int], List[int]]]) -> Tuple[List[int], List[int]]:
            s_tok = list(sys_tokens)
            s_lab = list(sys_labels)
            for b_tok, b_lab in blocks:
                s_tok.extend(b_tok)
                s_lab.extend(b_lab)
            return s_tok, s_lab

        full_tok, full_lab = assemble(turn_blocks)

        if len(full_tok) > req_len:
            if not allow_turn_truncation:
                raise TruncationSafetyError(
                    f"Sequence length ({len(full_tok)}) exceeds limit ({req_len}) and truncation is disabled."
                )

            # Safe sliding-window truncation: drop earlier turn pairs from the left
            # Must always keep system prompt and the final turn pair (last user + last assistant)
            current_blocks = list(turn_blocks)
            while len(current_blocks) > 2:
                # Drop oldest user and assistant turns (first 2 blocks)
                current_blocks = current_blocks[2:]
                candidate_tok, candidate_lab = assemble(current_blocks)
                if len(candidate_tok) <= req_len:
                    full_tok, full_lab = candidate_tok, candidate_lab
                    break

            if len(full_tok) > req_len:
                # Even just system prompt + the single final user-assistant turn exceeds max_seq_len!
                # Do NOT truncate the assistant target or prompt; reject the example as oversized.
                raise TruncationSafetyError(
                    f"Immediate turn pair length ({len(full_tok)} tokens) exceeds context limit ({req_len})."
                )

        # Causal language modeling target shift:
        # inputs = full_tok[:-1]
        # targets = full_lab[1:]
        inputs = full_tok[:-1]
        targets = full_lab[1:]

        # Sanity check lengths
        assert len(inputs) == len(targets), "Inputs and targets must have identical length after shift."
        assert len(inputs) <= max_seq_len, f"Inputs length {len(inputs)} exceeds {max_seq_len}."

        # Verify that at least one active (non -100) target exists
        num_active_targets = sum(1 for t in targets if t != IGNORE_INDEX)
        if num_active_targets == 0:
            raise ValueError("Conversation encoding resulted in 0 active assistant targets.")

        return inputs, targets
