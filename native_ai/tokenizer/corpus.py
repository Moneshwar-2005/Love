"""Seed Corpus Generation and Provenance Management for LOVE Native AI Tokenizer.

Implements Task 5:
- Generates a diverse, high-coverage English seed corpus for BPE tokenizer training.
- Generates a strictly separated held-out evaluation corpus for Task 9 benchmarks.
- Provenance: 100% Original, synthetically generated and curated technical, conversational,
  and general-purpose English prose dedicated to CC0 / Public Domain.
- Zero copyrighted text, zero personal data (PII), zero private user conversations.
- Computes SHA-256 checksums, enforces deduplication, and writes dataset manifests.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASETS_DIR = PROJECT_ROOT / "native_ai" / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
MANIFESTS_DIR = DATASETS_DIR / "manifests"


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_technical_prose() -> List[str]:
    """Generates varied technical and computer science articles."""
    articles = [
        """The Central Processing Unit, or CPU, is the primary computational engine of modern computer systems.
A modern CPU consists of several critical components: the Arithmetic Logic Unit (ALU), the Control Unit (CU),
registers for high-speed temporary storage, and a hierarchical memory cache comprising L1, L2, and L3 caches.
Instructions are retrieved from main system memory via the instruction fetch pipeline, decoded into micro-operations,
and dispatched to execution units. Superscalar processor architectures can execute multiple instructions per clock cycle
through instruction-level parallelism, speculative execution, and dynamic out-of-order scheduling.""",

        """Memory hierarchies in computing systems bridge the speed gap between high-frequency processors and bulk storage.
At the pinnacle of the hierarchy are processor registers, accessible within a single processor clock cycle.
Below registers lie multiple tiers of SRAM-based cache memory: Level 1 cache provides ultra-low latency,
Level 2 offers larger capacity with minor latency penalties, and Level 3 cache is typically shared among multiple cores.
Random Access Memory (DRAM) serves as the working primary memory, while persistent solid-state drives (SSD) and
hard disk drives (HDD) provide high-capacity, non-volatile long-term storage.""",

        """Graphics Processing Units (GPUs) specialize in massively parallel throughput computing.
Unlike CPUs, which emphasize low-latency sequential thread execution with complex branch predictors and large caches,
GPUs dedicate the vast majority of their silicon area to thousands of energy-efficient arithmetic logic units.
Modern deep learning frameworks harness this parallelism by formulating neural network forward and backward passes
as high-dimensional matrix multiplications, tensor contractions, and elementwise activation functions.""",

        """Transformer architectures rely on the attention mechanism to capture long-range contextual relationships.
In self-attention, input tokens are mapped into query, key, and value representation vectors through learned linear projections.
The dot product between queries and keys produces an unnormalized attention score matrix.
Dividing these scores by the square root of the head dimension prevents gradient saturation in regions with large magnitudes.
A softmax function normalizes the scores into attention probabilities, which weight the corresponding value vectors.""",

        """Operating systems manage hardware abstractions and orchestrate system resources among competing processes.
Kernel space manages physical memory via virtual memory paging tables, schedules thread execution on CPU cores,
and interfaces with peripheral devices through device drivers. User space applications execute within isolated
virtual address spaces, invoking kernel services via standardized system calls and application programming interfaces."""
    ]
    return articles


def generate_conversational_dialogues() -> List[str]:
    """Generates multi-turn conversational interactions utilizing LOVE special tokens."""
    dialogues = [
        """<|system|>You are LOVE, an intelligent, helpful, and concise native AI companion.<|user|>Explain the difference between synchronous and asynchronous input/output in software engineering.<|assistant|>Synchronous I/O halts thread execution until a requested operation completes, guaranteeing sequential predictability at the expense of computational idle time. In contrast, asynchronous I/O initiates the request and immediately yields thread control back to the event loop, notifying the application upon completion via callbacks, promises, or async/await state machines.""",

        """<|system|>You are LOVE, a native language model built for local execution.<|user|>How does Byte-Pair Encoding handle rare or unseen vocabulary words?<|assistant|>Byte-Pair Encoding (BPE) handles rare or compound words by segmenting them into known subword units or individual characters. When built at the byte level, any unseen Unicode character or out-of-vocabulary word gracefully decomposes into its constituent UTF-8 byte tokens, ensuring zero out-of-vocabulary exceptions.""",

        """<|system|>You are LOVE, an AI assistant with tool execution capabilities.<|user|>Please check the current available VRAM on device 0.<|assistant|><|tool|>Calling nvidia_smi(query="memory.free") -> 2256 MiB<|assistant|>Device 0 currently reports 2,256 MiB of available video memory.""",

        """<|system|>You are LOVE.<|user|>Write a concise Python function to calculate the Fibonacci sequence iteratively.<|assistant|>```python
def fibonacci(n: int) -> list[int]:
    if n <= 0:
        return []
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]
```
This implementation operates in O(n) linear time complexity and O(n) auxiliary space complexity."""
    ]
    return dialogues


def generate_general_prose_and_vocabulary() -> List[str]:
    """Generates rich English descriptive prose, vocabulary lists, and linguistic patterns."""
    samples = [
        """The early morning mist drifted silently across the pine-covered hills. Sunlight pierced through the dense forest canopy,
illuminating drops of crystalline dew suspended upon evergreen needles. Below in the valley, a winding freshwater stream
carved its path through ancient granite boulders, singing a perpetual song of erosion and renewal.
Nature proceeds with unhurried purpose, indifferent to the hurried cadence of human ambition.""",

        """Grammatical variety and syntactic diversity are fundamental to robust language modeling.
Standard English encompasses simple declarative sentences, compound structures joined by coordinating conjunctions,
complex clauses governed by subordinating markers, and interrogative expressions seeking clarification.
Punctuation marks—such as commas, colons, semicolons, dashes, apostrophes, quotation marks, and brackets—delineate
semantic boundaries and cadence.""",

        """Numerical notations, mathematical operators, and formatted quantities occur frequently in text:
Values such as 0, 1, 42, 3.14159, 2.71828, -100, 1,000,000, and $150.75 require accurate tokenization.
Dates and timestamps formatted as 2026-11-21, 18:30:00 UTC, or November 21, 2026 must be faithfully encoded.
Mathematical expressions like f(x) = ax^2 + bx + c, integral calculus formulas, and matrix dimensions like [256, 768]
demonstrate how symbols, digits, and alphabetic characters interact in structured documents.""",

        """Common abbreviations, contractions, and internet identifiers:
Contractions: don't, won't, haven't, shouldn't, it's, they're, we've, you'll, I'm.
Abbreviations: etc., e.g., i.e., vs., et al., API, CPU, GPU, VRAM, HTTP, HTTPS, UTF-8, JSON, YAML.
Identifiers: https://love.local/v1/models?format=json#metadata, admin@domain.internal, /usr/local/bin/python."""
    ]
    return samples


def generate_lexicon_corpus() -> List[str]:
    """
    Generates a comprehensive English vocabulary and morphological corpus
    to ensure the BPE tokenizer acquires a full 8,192 vocabulary target.
    Contains standard English word stems, grammatical inflections, technical terms,
    conversational phrases, and syntactic patterns.
    """
    # Base word stems across semantic categories
    word_stems = [
        # Computing & Engineering
        "access", "address", "allocate", "analog", "apply", "archive", "array", "assemble", "async", "atomic",
        "audio", "authenticate", "automate", "backend", "bandwidth", "binary", "binding", "block", "boolean",
        "branch", "broadcast", "buffer", "builder", "byte", "cache", "callback", "channel", "circuit", "client",
        "cloud", "cluster", "codec", "command", "compile", "compute", "concurrency", "config", "connect", "console",
        "constant", "context", "control", "convert", "core", "crypto", "cursor", "daemon", "database", "debug",
        "decode", "decrypt", "default", "delegate", "delete", "deploy", "device", "diagnostic", "digital", "directory",
        "disable", "dispatch", "display", "distribute", "driver", "dynamic", "element", "embed", "emit", "enable",
        "encode", "encrypt", "engine", "entity", "enum", "error", "event", "execute", "export", "express",
        "extract", "factor", "factory", "failover", "feature", "fetch", "fiber", "field", "filter", "firmware",
        "float", "format", "fragment", "frame", "frontend", "function", "gateway", "generate", "global", "gradient",
        "graphic", "handle", "hardware", "hash", "header", "heap", "hierarchy", "host", "hybrid", "hyperlink",
        "identifier", "immutable", "implement", "import", "index", "inference", "inherit", "init", "input", "insert",
        "install", "instance", "instruction", "integer", "integrate", "interface", "interrupt", "invoke", "iterate",
        "kernel", "keyboard", "latency", "layer", "layout", "legacy", "library", "lifecycle", "limit", "linear",
        "link", "listen", "literal", "load", "local", "lock", "logging", "logical", "lookup", "loop",
        "machine", "macro", "mailbox", "main", "manage", "manifest", "matrix", "memory", "merge", "message",
        "metadata", "method", "metric", "micro", "middleware", "migrate", "module", "monitor", "mount", "mutex",
        "namespace", "native", "navigate", "network", "neural", "node", "norm", "null", "numeric", "object",
        "offset", "operand", "operate", "optimize", "option", "output", "overflow", "override", "packet", "page",
        "palette", "parallel", "param", "parse", "partition", "patch", "path", "payload", "pipeline", "pixel",
        "platform", "plugin", "pointer", "policy", "port", "portal", "position", "precision", "predict", "prefix",
        "primitive", "priority", "process", "profile", "program", "prompt", "property", "protocol", "prototype",
        "provider", "proxy", "query", "queue", "quota", "random", "raster", "reactive", "read", "realtime",
        "record", "recover", "recurse", "redirect", "redundant", "refactor", "reference", "register", "registry",
        "release", "reload", "remote", "render", "repeat", "repository", "request", "resolve", "resource", "response",
        "restore", "retry", "return", "router", "routine", "runtime", "sample", "sandbox", "scalar", "scale",
        "scan", "schedule", "schema", "scope", "script", "scroll", "search", "secure", "segment", "select",
        "semantic", "semaphore", "sensor", "sequence", "serial", "server", "service", "session", "shader", "shadow",
        "shard", "signal", "signature", "simulate", "socket", "software", "source", "span", "spatial", "spec",
        "stack", "stage", "standard", "state", "static", "statistic", "status", "storage", "stream", "string",
        "structure", "style", "subagent", "subnet", "subroutine", "subscribe", "subsystem", "suffix", "symbol",
        "sync", "syntax", "system", "table", "target", "task", "telemetry", "template", "terminal", "terminate",
        "texture", "thread", "threshold", "timer", "token", "toolkit", "topology", "trace", "track", "traffic",
        "transaction", "transfer", "transform", "transistor", "translate", "transmit", "traverse", "trigger",
        "truncate", "tunnel", "type", "unified", "uniform", "unit", "unpack", "update", "upgrade", "upload",
        "utility", "validate", "value", "variable", "vector", "vendor", "verify", "version", "vertex", "video",
        "virtual", "visual", "volatile", "volume", "vulnerability", "watchdog", "webhook", "widget", "window",
        "wireless", "worker", "workflow", "workstation", "wrapper", "write", "yield", "zero", "zone",
        # Science & Mathematics
        "algebra", "amplitude", "angle", "anomaly", "approximate", "astronomy", "atom", "axiom", "axis",
        "bacteria", "biology", "calculus", "capacity", "catalyst", "cellular", "charge", "chemical", "chemistry",
        "coefficient", "collision", "complex", "compound", "conservation", "continuum", "coordinate", "corpus",
        "correlation", "crystal", "decay", "density", "derivative", "diffusion", "dimension", "discharge",
        "discrete", "dispersion", "distance", "divergence", "dynamics", "ecology", "electron", "elemental",
        "emission", "empirical", "energy", "entropy", "equilibrium", "evolution", "experiment", "exponential",
        "fluid", "force", "formula", "frequency", "friction", "galaxy", "gaussian", "gene", "genetic", "geometry",
        "gravity", "harmonic", "hypothesis", "inertia", "integral", "intensity", "isotope", "kinetic", "laser",
        "latitude", "light", "longitude", "magnitude", "mass", "mathematics", "mechanism", "molecule", "momentum",
        "mutation", "neutron", "nuclear", "nucleus", "orbit", "organic", "oscillation", "particle", "periodic",
        "phase", "phenomenon", "photon", "physics", "plasma", "polar", "potential", "pressure", "probability",
        "proton", "quantum", "radiation", "radius", "reaction", "refraction", "relativity", "resonance", "rotation",
        "satellite", "scalar", "science", "sediment", "solar", "spectrum", "stochastic", "symmetry", "temperature",
        "theorem", "theory", "thermal", "thermodynamics", "torque", "trajectory", "universe", "velocity", "vibration",
        "voltage", "volume", "vortex", "wave", "wavelength",
        # General English Literature & Common Vocabulary
        "ability", "above", "accept", "accident", "accord", "account", "achieve", "acquire", "across", "action",
        "active", "actual", "adapt", "addition", "advance", "advantage", "adventure", "advice", "affect", "afford",
        "afraid", "after", "again", "against", "agency", "agree", "ahead", "airport", "alarm", "alcohol",
        "alert", "alien", "alive", "alleged", "allow", "almost", "alone", "along", "already", "alright",
        "also", "alter", "although", "always", "amaze", "ambition", "among", "amount", "amuse", "ancient",
        "anger", "angle", "angry", "animal", "annual", "another", "answer", "anticipate", "anxiety", "anybody",
        "anyone", "anything", "anyway", "anywhere", "apart", "apartment", "apology", "apparent", "appeal", "appear",
        "apple", "appoint", "appreciate", "approach", "approve", "approximate", "architect", "area", "argue", "arise",
        "armor", "around", "arrange", "arrest", "arrival", "arrive", "arrow", "article", "artist", "ashamed",
        "aside", "asleep", "aspect", "aspire", "assault", "assert", "assess", "asset", "assign", "assist",
        "associate", "assume", "assure", "astonish", "athlete", "atmosphere", "attach", "attack", "attain", "attempt",
        "attend", "attitude", "attract", "attribute", "audience", "author", "authority", "automatic", "autumn",
        "available", "avenue", "average", "avoid", "awake", "award", "aware", "balance", "banner", "barely",
        "bargain", "barrier", "battle", "beauty", "become", "before", "behave", "belief", "belong", "beneath",
        "benefit", "beside", "between", "beyond", "billion", "blanket", "blessing", "boundary", "bravery", "breathe",
        "brilliant", "brother", "building", "burden", "business", "cabinet", "calendar", "calmness", "campaign",
        "candidate", "capable", "captain", "capture", "careful", "carrier", "cascade", "category", "caution",
        "celebrate", "century", "certain", "chamber", "champion", "chapter", "charity", "charming", "chronic",
        "citizen", "classic", "climate", "clothing", "coastal", "cognition", "collect", "college", "colony",
        "combine", "comfort", "command", "comment", "commerce", "commit", "committee", "companion", "compare",
        "compassion", "compensate", "compete", "competent", "complain", "complete", "component", "compose", "compound",
        "comprehend", "comprehensive", "compromise", "conceal", "concept", "concern", "conclude", "concrete",
        "condition", "conduct", "confer", "confidence", "confirm", "conflict", "conform", "confront", "confuse",
        "congratulate", "congress", "connect", "conquer", "conscience", "conscious", "consensus", "consent",
        "consequence", "conserve", "consider", "consist", "consistent", "constant", "constitute", "construct",
        "consult", "consume", "contact", "contain", "contemporary", "content", "contest", "context", "continent",
        "continue", "continuous", "contract", "contrary", "contrast", "contribute", "convenient", "convention",
        "converge", "conversation", "convey", "convince", "cooperate", "coordinate", "corporate", "correspond",
        "corridor", "costume", "cottage", "council", "counsel", "courage", "courtesy", "covenant", "coverage",
        "creative", "creature", "credibility", "criminal", "crisis", "criteria", "critical", "crucial", "crystal",
        "culture", "curious", "current", "custom", "cylinder", "damage", "danger", "darkness", "database",
        "daughter", "daylight", "deadline", "dealings", "debate", "debris", "decade", "deceive", "decency",
        "decision", "decisive", "declare", "decline", "decorate", "decrease", "dedicate", "deduce", "defense",
        "defend", "deficiency", "deficit", "definite", "definition", "delegate", "deliberate", "delicate", "delight",
        "delivery", "demand", "democracy", "demolish", "demonstrate", "denial", "density", "depart", "departure",
        "depend", "depict", "deposit", "depress", "depth", "deputy", "derive", "descend", "describe", "description",
        "desert", "deserve", "design", "desire", "despair", "desperate", "destination", "destiny", "destroy",
        "destruction", "detail", "detect", "determine", "develop", "device", "devote", "dialogue", "diary",
        "dictate", "differ", "difference", "difficult", "digest", "dignity", "diligent", "dimension", "diminish",
        "dilemma", "diplomat", "director", "disaster", "discard", "discern", "discipline", "disclose", "discount",
        "discourse", "discover", "discreet", "discretion", "discuss", "disease", "disguise", "disgust", "dismiss",
        "disorder", "displace", "display", "disposal", "dispute", "disrupt", "dissolve", "distant", "distinct",
        "distinguish", "distort", "distract", "distress", "distribute", "district", "disturb", "diverse", "divert",
        "divide", "divine", "divorce", "doctrine", "document", "domain", "domestic", "dominant", "dominate",
        "donation", "doubtful", "dramatic", "drastic", "dreadful", "duration", "dwelling", "dynamic", "eagerly",
        "earnest", "earnings", "earthquake", "eccentric", "echoing", "economic", "economy", "ecstasy", "edition",
        "educate", "effective", "efficacy", "efficient", "effort", "elaborate", "elastic", "elderly", "electric",
        "elegant", "elevation", "eligible", "eliminate", "elite", "eloquent", "embrace", "emerge", "emergency",
        "emission", "emotion", "emphasis", "empirical", "employ", "empower", "emulate", "enact", "enchant",
        "enclose", "encounter", "encourage", "endeavor", "endless", "endorse", "endure", "energetic", "enforce",
        "engage", "engine", "enhance", "enigma", "enjoyment", "enormous", "enrich", "enterprise", "entertain",
        "enthusiasm", "entire", "entitle", "entity", "entrance", "envelope", "environment", "episode", "equality",
        "equation", "equator", "equip", "equivalent", "eradicate", "erosion", "erratic", "erupt", "escalate",
        "escape", "escort", "especially", "essay", "essential", "establish", "estate", "esteem", "estimate",
        "eternal", "ethic", "evaluate", "evaporate", "eventual", "evident", "evolution", "exact", "exaggerate",
        "examine", "example", "exceed", "excellent", "exception", "excess", "exchange", "excite", "exclude",
        "exclusive", "excursion", "execute", "exempt", "exercise", "exhaust", "exhibit", "exile", "exist",
        "exit", "exotic", "expand", "expect", "expedite", "expedition", "expense", "experience", "experiment",
        "expert", "explain", "explicit", "explode", "exploit", "explore", "explosion", "export", "expose",
        "express", "exquisite", "extend", "extensive", "extent", "exterior", "external", "extinct", "extra",
        "extract", "extraordinary", "extreme", "facility", "factor", "faculty", "failure", "faithful", "familiar",
        "famine", "fantastic", "farewell", "fascinate", "fashion", "fatigue", "feasible", "feature", "federal",
        "feedback", "felicity", "fellowship", "feminine", "ferocious", "fertile", "festival", "fidelity", "fierce",
        "figure", "filament", "finalize", "finance", "financial", "finite", "flame", "flawless", "flexible",
        "flourish", "fluctuate", "fluid", "forecast", "foreigner", "foresee", "forever", "forgive", "formal",
        "formula", "formulate", "forthcoming", "fortunate", "forward", "foster", "foundation", "fraction", "fragile",
        "fragment", "framework", "frankly", "frantic", "fraud", "freedom", "freight", "frequency", "friction",
        "frontier", "frustrate", "fulfill", "fundamental", "furious", "furnish", "furniture", "further", "futile",
        "galaxy", "gallant", "gallery", "gamble", "garment", "garrison", "gateway", "gather", "general",
        "generate", "generation", "generous", "genius", "genuine", "geography", "geometry", "gesture", "gigantic",
        "glance", "glimpse", "glimmer", "glimpse", "glorious", "goodness", "gorgeous", "govern", "government",
        "graceful", "gradual", "graduate", "grammar", "grandeur", "graphic", "grateful", "gratitude", "gravity",
        "grievance", "grimace", "grotesque", "guarantee", "guardian", "guidance", "guideline", "guilty", "gulf",
        "habitat", "habitual", "harmony", "harvest", "hazard", "heading", "headquarters", "healthy", "heartfelt",
        "heavenly", "heavily", "heritage", "hesitate", "hierarchy", "highway", "hilarity", "historic", "hitherto",
        "holistic", "homage", "homeless", "homework", "honesty", "horizon", "horizontal", "horrible", "hospital",
        "hostile", "household", "humanity", "humble", "humidity", "humorous", "hundred", "hurricane", "hygiene",
        "hypocrisy", "hypothesis", "hysteria", "identical", "identify", "identity", "ideology", "idiomatic",
        "ignorance", "illegal", "illuminate", "illusion", "illustrate", "image", "imagery", "imagination", "imitate",
        "immense", "immerse", "imminent", "immortal", "immunity", "impact", "impartial", "impatience", "impede",
        "imperative", "imperfect", "imperial", "impetus", "implement", "implication", "implicit", "implore",
        "importance", "impossible", "impress", "imprison", "improve", "impulse", "inability", "inaccurate",
        "inadequate", "inaugurate", "incentive", "incidence", "incident", "incision", "incline", "include",
        "inclusive", "income", "incompetent", "incomplete", "incorporate", "increase", "incredible", "indebted",
        "indecision", "indefinite", "independence", "indicate", "indifferent", "indigenous", "indignant", "indirect",
        "indispensable", "individual", "induce", "indulge", "industrial", "industry", "inequality", "inevitable",
        "infamous", "infant", "infect", "inferior", "infinite", "inflation", "influence", "inform", "informal",
        "ingenious", "ingenuity", "ingredient", "inhabit", "inherent", "inherit", "inhibit", "initial", "initiative",
        "inject", "injury", "injustice", "inland", "innocent", "innovate", "innumerable", "inquire", "inquiry",
        "insane", "inscription", "insect", "insecure", "insert", "insight", "insist", "inspect", "inspire",
        "install", "instance", "instant", "instead", "instinct", "institute", "instruct", "instrument", "insufficient",
        "insult", "insurance", "intact", "integral", "integrity", "intellect", "intelligence", "intelligent",
        "intend", "intense", "intent", "interact", "intercept", "interchange", "interest", "interface", "interfere",
        "interior", "intermediate", "internal", "international", "interpret", "interrupt", "intersect", "interval",
        "intervene", "intimate", "intimidate", "intricate", "intrigue", "intrinsic", "introduce", "intrude",
        "intuition", "invade", "invalid", "invariable", "invasion", "invent", "inventory", "inverse", "invest",
        "investigate", "invincible", "invisible", "invitation", "invoice", "invoke", "involve", "inward",
        "irrelevant", "irresistible", "isolate", "issue", "iterate", "itinerary", "jealousy", "jeopardy",
        "journal", "journey", "judgment", "judicial", "junction", "juncture", "jurisdiction", "justice", "justify",
        "juvenile", "keenness", "kernel", "kidnap", "kinetic", "kingdom", "kinship", "knighthood", "knowledge",
        "laborious", "labyrinth", "lament", "landscape", "language", "languish", "lantern", "latitude", "laudable",
        "laughter", "laundry", "lavish", "lawsuit", "layman", "layout", "leadership", "league", "leakage",
        "learned", "lease", "leather", "legacy", "legend", "legitimate", "leisure", "length", "leniency",
        "lesson", "leverage", "liability", "liberty", "library", "license", "lifelong", "likelihood", "limit",
        "limitation", "lineage", "linguistic", "liquidity", "literal", "literary", "literature", "livelihood",
        "lively", "location", "lodging", "logic", "lonely", "longitude", "longstanding", "lookout", "loophole",
        "lottery", "loyalty", "lucrative", "luggage", "luminous", "lunatic", "luxurious", "machinery", "magazine",
        "magistrate", "magnificent", "magnitude", "maiden", "mainstream", "maintain", "maintenance", "majesty",
        "majority", "maker", "manage", "management", "manager", "mandate", "manifest", "manipulate", "manner",
        "mansion", "manual", "manufacture", "manuscript", "marathon", "margin", "marine", "marital", "marketer",
        "marketplace", "marriage", "marshal", "martial", "marvel", "masculine", "massacre", "massive", "masterpiece",
        "matchless", "material", "maternal", "mathematics", "matrix", "mature", "maximum", "meadow", "meaning",
        "measure", "measurement", "mechanic", "mechanism", "mediate", "medical", "medicine", "medieval", "mediocre",
        "meditate", "medium", "melody", "membership", "memoir", "memorable", "memorial", "memory", "menace",
        "mental", "mention", "mentor", "merchandise", "merchant", "mercy", "merger", "merit", "message",
        "messenger", "metallic", "metaphor", "meteor", "meter", "method", "methodology", "metropolis", "microscope",
        "midday", "midnight", "midst", "mighty", "migrant", "migrate", "milestone", "military", "militia",
        "millennium", "million", "miniature", "minimal", "minimize", "minimum", "minister", "ministry", "minority",
        "miracle", "mirror", "mischief", "misery", "misfortune", "mislead", "mission", "mistake", "mistrust",
        "mixture", "mobilize", "modality", "moderate", "modern", "modest", "modify", "module", "molecule",
        "moment", "momentum", "monarch", "monastery", "monetary", "monitor", "monopoly", "monotonous", "monster",
        "monument", "morale", "morality", "morning", "mortality", "mortgage", "motion", "motivate", "motive",
        "motor", "mountain", "mourn", "movement", "multiple", "multiply", "multitude", "municipal", "murder",
        "muscle", "museum", "musical", "musician", "mustache", "mutation", "mutual", "myriad", "mysterious",
        "mystery", "mythology", "naivety", "narrative", "narrow", "nascent", "nation", "national", "native",
        "natural", "nature", "nausea", "navigate", "navigation", "nearby", "necessary", "necessity", "needle",
        "negative", "neglect", "negotiate", "neighbor", "neither", "nephew", "nervous", "nestle", "network",
        "neutral", "newcomer", "newspaper", "nibble", "nickname", "nightfall", "nightmare", "nobility", "nocturnal",
        "nominal", "nominate", "nonsense", "normative", "northern", "notable", "notary", "notation", "notice",
        "notify", "notion", "notorious", "novelty", "nowadays", "nuance", "nucleus", "nuisance", "nullify",
        "number", "numerical", "numerous", "nuptial", "nursery", "nurture", "nutrient", "nutrition", "oasis",
        "obedient", "obituary", "object", "objective", "obligate", "obligation", "oblige", "oblique", "oblivion",
        "obnoxious", "obscure", "observance", "observe", "observer", "obsess", "obsolete", "obstacle", "obstinate",
        "obstruct", "obtain", "obvious", "occasion", "occupant", "occupation", "occupy", "occurrence", "ocean",
        "offense", "offensive", "official", "offshore", "offspring", "omit", "omnipotent", "ongoing", "onset",
        "opacity", "openness", "opera", "operate", "operation", "operator", "opinion", "opponent", "opportune",
        "opportunity", "oppose", "opposite", "opposition", "oppress", "optics", "optimal", "optimism", "optimum",
        "optional", "oracle", "oration", "orator", "orbit", "orchestra", "orderly", "ordinance", "ordinary",
        "organic", "organism", "organize", "orient", "origin", "original", "ornament", "orthodox", "oscillate",
        "ostensible", "ostracize", "outcome", "outdated", "outdoor", "outfit", "outgoing", "outlaw", "outlet",
        "outline", "outlook", "output", "outrage", "outreach", "outset", "outside", "outspoken", "outstanding",
        "outward", "oval", "ovation", "overall", "overcome", "overdue", "overflow", "overhaul", "overhead",
        "overlap", "overlook", "overnight", "oversee", "oversight", "overthrow", "overture", "overwhelm", "ownership",
        "package", "packet", "pact", "pageant", "painful", "painting", "palace", "palette", "pamphlet",
        "panic", "panorama", "parable", "paradox", "paragraph", "parallel", "paralyze", "parameter", "paramount",
        "paraphrase", "parasite", "parcel", "pardon", "parental", "parity", "parliament", "parody", "parole",
        "partial", "participant", "participate", "particle", "particular", "partisan", "partition", "partner",
        "passage", "passenger", "passion", "passive", "passport", "pastime", "pasture", "patent", "pathway",
        "patience", "patient", "patriarch", "patriot", "patrol", "patron", "pattern", "pavement", "payment",
        "peaceful", "peasant", "peculiar", "pedestrian", "peerless", "penalty", "pendulum", "penetrate", "penitent",
        "pension", "perceive", "percent", "perception", "perennial", "perfect", "perform", "performance", "perfume",
        "perilous", "periodic", "periphery", "perish", "permanent", "permissible", "permission", "permit", "perpetual",
        "perplex", "persecute", "persevere", "persist", "personal", "personality", "personnel", "perspective",
        "persuade", "pertinent", "pervade", "pessimism", "petition", "petroleum", "phantom", "pharmacy", "phase",
        "phenomenon", "philosophy", "photograph", "phrase", "physical", "physician", "physics", "picturesque",
        "piercing", "pilgrim", "pillar", "pilot", "pinnacle", "pioneer", "pipeline", "piracy", "pitcher",
        "pivotal", "placard", "plague", "plainly", "plaintiff", "planetary", "planner", "platform", "plausible",
        "pleasant", "pleasure", "pledge", "plentiful", "plight", "plummet", "plural", "poetic", "poignant",
        "polar", "polarity", "police", "policy", "polish", "polite", "politics", "pollutant", "pollution",
        "polygon", "ponder", "popular", "population", "portal", "portfolio", "portion", "portrait", "portray",
        "position", "positive", "possess", "possession", "possibility", "possible", "postage", "poster", "postpone",
        "posture", "potent", "potential", "pottery", "poverty", "powerful", "practical", "practice", "practitioner",
        "praise", "preach", "precaution", "precede", "precedent", "precept", "precious", "precipice", "precise",
        "precision", "preclude", "predator", "predecessor", "predicament", "predicate", "predict", "prediction",
        "predominant", "preface", "prefer", "preference", "prefix", "pregnant", "prejudice", "preliminary",
        "premature", "premier", "premise", "premium", "premonition", "preoccupy", "preparation", "prepare",
        "prescribe", "presence", "present", "presentation", "preserve", "preside", "president", "press",
        "pressure", "prestige", "presume", "pretend", "pretense", "pretext", "prevail", "prevalent", "prevent",
        "previous", "primary", "primate", "prime", "primitive", "prince", "principal", "principle", "printed",
        "priority", "prison", "prisoner", "privacy", "private", "privilege", "prize", "probable", "probation",
        "probe", "problem", "procedure", "proceed", "proceeding", "process", "procession", "proclaim", "prodigy",
        "produce", "product", "production", "productive", "productivity", "profess", "profession", "professional",
        "professor", "proficient", "profile", "profit", "profitable", "profound", "program", "progress", "prohibit",
        "project", "projection", "prolific", "prolong", "prominent", "promise", "promote", "promotion", "prompt",
        "pronounce", "propaganda", "propel", "proper", "property", "prophecy", "prophet", "proportion", "proposal",
        "propose", "proposition", "proprietor", "prose", "prosecute", "prospect", "prosper", "prosperity",
        "protect", "protection", "protective", "protector", "protest", "protocol", "prototype", "protract",
        "proudly", "proven", "provide", "provided", "provider", "province", "provision", "provoke", "prudence",
        "prudent", "psychology", "public", "publication", "publicity", "publish", "publisher", "punctual",
        "punish", "punishment", "purchase", "purely", "purify", "purity", "purpose", "pursue", "pursuit",
        "puzzled", "pyramid", "quaint", "qualify", "quality", "quantity", "quarantine", "quarrel", "quarry",
        "quarter", "queen", "quench", "querulous", "query", "question", "questionnaire", "queue", "quickness",
        "quietly", "quiver", "quotation", "quote", "radiance", "radiant", "radiate", "radical", "radius",
        "raffle", "railway", "rainbow", "rally", "random", "ranger", "rapid", "rapidity", "rapture", "rarely",
        "rarity", "rashness", "ratify", "ratio", "rational", "rattle", "ravage", "reaction", "readiness",
        "readily", "realism", "realistic", "reality", "realize", "realm", "reap", "rear", "reasonable", "reassure",
        "rebellion", "rebound", "rebuke", "recall", "recede", "receipt", "receive", "receiver", "recent",
        "receptive", "recess", "recipe", "recipient", "reciprocal", "recite", "reckless", "reckon", "reclaim",
        "recognition", "recognize", "recoil", "recollect", "recommend", "recompense", "reconcile", "reconnaissance",
        "record", "recover", "recovery", "recreation", "recruit", "rectangle", "rectify", "recur", "recurrent",
        "recycle", "redeem", "redemption", "redirect", "redouble", "reduce", "reduction", "redundant", "referee",
        "reference", "refine", "reflect", "reflection", "reform", "refrain", "refresh", "refuge", "refugee",
        "refund", "refusal", "refuse", "refute", "regard", "regardless", "regenerate", "regime", "regiment",
        "region", "regional", "register", "registration", "regret", "regular", "regulate", "regulation", "rehabilitate",
        "rehearse", "reign", "reinforce", "reinvent", "reject", "rejection", "rejoice", "relapse", "relate",
        "relation", "relationship", "relative", "relax", "relaxation", "relay", "release", "relevant", "reliable",
        "reliance", "relic", "relief", "relieve", "religion", "religious", "relinquish", "relish", "reluctant",
        "rely", "remain", "remainder", "remark", "remarkable", "remedy", "remember", "remembrance", "remind",
        "remnant", "remorse", "remote", "removal", "remove", "renaissance", "render", "renew", "renewal",
        "renounce", "renovate", "renown", "repair", "repeal", "repeat", "repel", "repent", "repertoire",
        "repetition", "replace", "replenish", "replica", "reply", "report", "reporter", "repose", "represent",
        "representative", "repress", "reprieve", "reprimand", "reproach", "reproduce", "reptile", "repudiate",
        "repugnant", "repulse", "reputation", "request", "require", "requirement", "requisite", "rescue", "research",
        "resemblance", "resemble", "resent", "resentment", "reservation", "reserve", "reservoir", "reside",
        "residence", "resident", "residual", "resign", "resignation", "resilient", "resist", "resistance",
        "resolute", "resolution", "resolve", "resonance", "resort", "resource", "resourceful", "respect",
        "respectable", "respective", "respiration", "respite", "respond", "respondent", "response", "responsibility",
        "responsible", "restoration", "restore", "restrain", "restraint", "restrict", "restriction", "result",
        "resume", "resurgence", "retail", "retain", "retaliate", "retention", "reticent", "retire", "retirement",
        "retort", "retract", "retreat", "retribution", "retrieve", "retrospect", "return", "reveal", "revelation",
        "revenge", "revenue", "reverence", "reverse", "reversion", "review", "revise", "revision", "revival",
        "revive", "revoke", "revolt", "revolution", "revolutionary", "revolve", "reward", "rhetoric", "rhythm",
        "rhythmic", "ribbon", "riddle", "ridiculous", "righteous", "rigid", "rigor", "rigorous", "ringleader",
        "rival", "rivalry", "riverbank", "roadway", "robust", "romance", "romantic", "rooftop", "rotate",
        "rotation", "roughness", "routine", "royal", "royalty", "rudiment", "rugged", "ruinous", "rumor",
        "rupture", "rural", "rustic", "ruthless", "sabotage", "sacred", "sacrifice", "safeguard", "sagacity",
        "salient", "salvation", "sanction", "sanctuary", "sarcasm", "satisfaction", "satisfactory", "satisfy",
        "saturate", "savage", "scandal", "scarce", "scarcity", "scenario", "scenery", "scent", "schedule",
        "scheme", "scholar", "scholarship", "scientific", "scientist", "scramble", "scrutiny", "sculpture",
        "seaboard", "seafaring", "seamless", "season", "seasonal", "secession", "seclude", "second", "secondary",
        "secrecy", "secret", "secretary", "section", "secular", "secure", "security", "sedate", "sediment",
        "segment", "segregate", "seizure", "seldom", "select", "selection", "selective", "senate", "senator",
        "sensation", "sensible", "sensitive", "sensory", "sentence", "sentiment", "separate", "separation",
        "sequence", "serene", "serenity", "sergeant", "serial", "series", "serious", "sermon", "servant",
        "service", "session", "settle", "settlement", "severe", "severity", "shallow", "shameful", "shelter",
        "sheriff", "shipment", "shortage", "shortcoming", "shortly", "shrewd", "shrink", "shudder", "sibling",
        "signal", "signature", "significance", "significant", "signify", "silence", "silent", "similar",
        "similarity", "simple", "simplicity", "simplify", "simulate", "simulation", "simultaneous", "sincere",
        "sincerity", "singular", "sinister", "situation", "skeptical", "skeleton", "skillful", "slumber",
        "sociable", "social", "society", "soldier", "solemn", "solicit", "solid", "solidarity", "solitary",
        "solitude", "solution", "solvent", "somewhat", "sophisticated", "sorrow", "soundness", "sovereign",
        "sovereignty", "spacious", "sparkle", "spatial", "special", "specialist", "specialize", "species",
        "specific", "specify", "specimen", "spectacle", "spectacular", "spectator", "spectrum", "speculate",
        "speculation", "speech", "spherical", "splendid", "splendor", "spontaneous", "sporadic", "spotless",
        "spouse", "sprightly", "stadium", "stagnant", "stamina", "standard", "standpoint", "startle", "statehood",
        "statesman", "static", "stationary", "stationery", "statistic", "statue", "stature", "status", "statute",
        "steadfast", "steady", "stealth", "stimulate", "stimulus", "stipulate", "stochastic", "stockholder",
        "straightforward", "stranger", "strategic", "strategy", "strength", "strenuous", "striking", "structure",
        "struggle", "stubborn", "student", "studio", "studious", "subject", "subjective", "submarine", "submerge",
        "submission", "submit", "subordinate", "subscribe", "subsequent", "subside", "subsidiary", "subsidy",
        "subsist", "substance", "substantial", "substitute", "subtle", "subtlety", "subtract", "suburb",
        "subversion", "succeed", "success", "successful", "succession", "successive", "successor", "succinct",
        "sudden", "sufficient", "suffocate", "suggest", "suggestion", "suicide", "suitable", "summary",
        "summit", "summon", "superb", "superficial", "superfluous", "superior", "supernatural", "supersede",
        "supervise", "supplant", "supplement", "supplier", "supply", "support", "suppose", "suppress",
        "supreme", "surface", "surgeon", "surgery", "surmise", "surmount", "surpass", "surplus", "surprise",
        "surrender", "surround", "surveillance", "survey", "survival", "survive", "survivor", "susceptible",
        "suspect", "suspend", "suspense", "suspicion", "suspicious", "sustain", "sustainable", "sustenance",
        "swallow", "swiftness", "syllable", "symbol", "symbolic", "symmetry", "sympathetic", "sympathy",
        "symptom", "synchronize", "syndicate", "synonym", "synopsis", "synthesis", "synthetic", "systematic",
        "tactful", "tactics", "talent", "talented", "talisman", "tangible", "tantalize", "tapestry", "tariff",
        "taxation", "technical", "technique", "technology", "tedious", "telecom", "telegraph", "telephone",
        "telescope", "temperament", "temperate", "temperature", "tempest", "temporal", "temporary", "temptation",
        "tenacious", "tenacity", "tendency", "tenant", "tender", "tension", "tentative", "tenure", "terminal",
        "terminate", "terminology", "terrace", "terrestrial", "terrible", "terrific", "terrify", "territory",
        "terror", "terrorism", "testament", "testify", "testimony", "textbook", "textile", "texture", "theater",
        "theft", "thematic", "theme", "theology", "theoretical", "theorist", "theory", "therapeutic", "therapy",
        "thermal", "thesis", "thickness", "thoughtful", "threat", "threaten", "threshold", "thrift", "thrive",
        "throughout", "thunder", "tide", "tighten", "timber", "timeline", "timely", "timidity", "tiresome",
        "title", "token", "tolerance", "tolerant", "tolerate", "topography", "torment", "tornado", "torpedo",
        "torrent", "torture", "totalitarian", "touchstone", "tournament", "toward", "toxic", "traceable",
        "trademark", "tradition", "traditional", "tragedy", "tragic", "traitor", "trajectory", "trample",
        "tranquil", "tranquility", "transaction", "transcend", "transcribe", "transcript", "transfer", "transform",
        "transformation", "transient", "transistor", "transit", "transition", "translate", "translation",
        "transmission", "transmit", "transparent", "transport", "transportation", "transpose", "traverse",
        "treachery", "treasure", "treasury", "treatise", "treatment", "treaty", "tremble", "tremendous",
        "tremor", "trench", "trend", "trespass", "tribal", "tribunal", "tributary", "tribute", "trigger",
        "triumph", "triumphant", "trivial", "troublesome", "truancy", "truce", "trumpet", "trustee", "trustworthy",
        "tumult", "turbulent", "turmoil", "twilight", "typical", "tyrannical", "tyranny", "tyrant", "ubiquitous",
        "ultimate", "ultimately", "ultimatum", "unanimous", "uncertain", "uncommon", "unconscious", "undercover",
        "undergo", "undergraduate", "underline", "underlying", "undermine", "underneath", "understand",
        "understanding", "undertake", "undertaking", "underwrite", "undoubted", "uneasy", "unemployed",
        "unequal", "unexpected", "unfair", "unfamiliar", "unfavorable", "unfold", "unforeseen", "unfortunate",
        "uniform", "uniformity", "unify", "unilateral", "unique", "unison", "unit", "unite", "unity",
        "universal", "universe", "university", "unjust", "unknown", "unlawful", "unlimited", "unlock",
        "unprecedented", "unpredictable", "unravel", "unreasonable", "unrest", "unrivaled", "unruly", "unsettled",
        "unstable", "unsuccessful", "unthinkable", "untidy", "untold", "unusual", "unveil", "unwarranted",
        "unwieldy", "unwilling", "unworthy", "upgrade", "upheaval", "uphold", "uplifting", "upon", "upper",
        "upright", "uprising", "uproar", "uproot", "upset", "upstream", "upward", "urban", "urgency", "urgent",
        "usage", "useful", "useless", "usher", "usual", "usurp", "utensil", "utility", "utilize", "utmost",
        "utopia", "utopian", "utterance", "vacancy", "vacant", "vacate", "vacation", "vaccinate", "vacuum",
        "vague", "vain", "valiant", "valid", "validate", "validity", "valley", "valuable", "valuation", "value",
        "vanish", "vanity", "vanquish", "variable", "variation", "variety", "various", "varnish", "vascular",
        "vault", "vector", "vegetable", "vegetation", "vehemence", "vehicle", "velocity", "venerable", "venerate",
        "vengeance", "venture", "venue", "veracity", "verdict", "verge", "verification", "verify", "veritable",
        "versatile", "versatility", "version", "vertical", "veteran", "viable", "vibrant", "vibrate", "vibration",
        "vicar", "vicinity", "vicious", "victim", "victorious", "victory", "vigilance", "vigilant", "vigor",
        "vigorous", "village", "villain", "vindicate", "vineyard", "violate", "violation", "violence", "violent",
        "virtual", "virtue", "virtuous", "visible", "vision", "visionary", "visit", "visitor", "visual",
        "visualize", "vital", "vitality", "vivid", "vividly", "vocal", "vocation", "vocational", "volatile",
        "volatility", "volcano", "volition", "voltage", "volume", "voluntary", "volunteer", "vortex", "vow",
        "voyage", "vulnerability", "vulnerable", "wafer", "wager", "waking", "walkway", "warfare", "warlike",
        "warmth", "warrant", "warranty", "warrior", "watchful", "waterfall", "waterproof", "watershed", "wavelength",
        "wayward", "weakness", "wealth", "wealthy", "weapon", "weariness", "weather", "weave", "website",
        "wedlock", "weighty", "welcome", "welfare", "western", "whereabouts", "whereas", "whereby", "whereupon",
        "wholesome", "widespread", "wildcat", "wilderness", "wildfire", "wildlife", "willing", "windfall",
        "windmill", "windpipe", "windstorm", "winsome", "wireless", "wisdom", "wistful", "withdraw", "withdrawal",
        "withhold", "withstand", "witness", "woeful", "wonderful", "workaday", "workbench", "workforce", "workhorse",
        "workman", "workplace", "workshop", "worldliness", "worldwide", "worship", "worthwhile", "worthless",
        "wreckage", "wretched", "wrestle", "writer", "writhe", "wrongdoing", "xenon", "xerox", "yacht", "yearbook",
        "yearling", "yearlong", "yearly", "yearning", "yeast", "yellowish", "yesterday", "yield", "yielding",
        "youthful", "zeal", "zealot", "zealous", "zenith", "zephyr", "zero", "zigzag", "zirconium", "zodiac", "zonal", "zone"
    ]

    # Generate rich syntactic combinations and sentences
    sentences = []
    # 1. Individual word definitions & usages
    for w in word_stems:
        sentences.append(f"The term {w} represents an important English concept.")
        sentences.append(f"In standard practice, {w} and its related forms appear frequently across written documents.")
        sentences.append(f"Researchers observe {w} in technical literature, conversational discourse, and academic writing.")

    # 2. Pairwise and compound associations
    for i in range(0, len(word_stems) - 1, 3):
        w1 = word_stems[i]
        w2 = word_stems[i+1]
        w3 = word_stems[i+2]
        sentences.append(f"Analyzing {w1} alongside {w2} highlights fundamental interactions concerning {w3}.")
        sentences.append(f"Both {w1} and {w2} provide necessary context when evaluating {w3} in formal systems.")

    # Morphological derivations and linguistic inflections
    common_suffixes = ["s", "ed", "ing", "ly", "er", "able", "ment", "ness", "tion", "ive", "al", "ic", "ity", "ous"]
    common_prefixes = ["un", "re", "pre", "dis", "sub", "inter", "anti", "non", "multi", "micro", "hyper"]
    for w in word_stems:
        derivations = [w]
        for s in common_suffixes:
            derivations.append(w + s)
        for p in common_prefixes:
            derivations.append(p + w)
        sentences.append(f"Morphological forms for {w}: {' '.join(derivations)}.")

    return sentences


def generate_expanded_seed_corpus() -> Tuple[str, str]:
    """
    Assembles the full seed corpus and held-out evaluation corpus.
    Applies variations and combinatorial topic expansions to ensure thorough
    vocabulary and n-gram coverage across the entire 8,192 BPE target space.
    """
    technical = generate_technical_prose()
    conversational = generate_conversational_dialogues()
    general = generate_general_prose_and_vocabulary()
    lexicon_sentences = generate_lexicon_corpus()

    all_docs: List[str] = []
    # Add core blocks
    all_docs.extend(technical)
    all_docs.extend(conversational)
    all_docs.extend(general)
    all_docs.extend(lexicon_sentences)

    # Scientific and conversational prompt repeats for natural n-gram statistical weighting
    for doc in technical:
        all_docs.append(doc)
    for doc in conversational:
        all_docs.append(doc)

    # Deduplicate while preserving order
    seen_hashes = set()
    unique_docs: List[str] = []
    for doc in all_docs:
        h = compute_sha256(doc)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_docs.append(doc)

    training_text = "\n\n".join(unique_docs)

    # Create strictly held-out evaluation text (NEVER included in training corpus)
    held_out_docs = [
        """Held-out evaluation sample 1: The intersection of discrete mathematics and formal language theory
provides the foundational underpinning for modern compiler construction and lexical analysis.
Deterministic finite automata scan token streams, verifying lexical legality against regular expressions
before syntax parsing trees are generated.""",

        """Held-out evaluation sample 2: High-performance parallel algorithms require careful synchronization primitives
to avoid race conditions, deadlocks, and memory corruption. Mutexes, semaphores, atomic compare-and-swap operations,
and lock-free ring buffers each offer distinct performance trade-offs in multi-threaded application design.""",

        """<|system|>Held-out test interaction.<|user|>Can you calculate 17 multiplied by 23 and format it as JSON?<|assistant|>```json
{
  "operation": "multiplication",
  "operands": [17, 23],
  "result": 391
}
```"""
    ]
    held_out_text = "\n\n".join(held_out_docs)

    return training_text, held_out_text


def build_and_save_corpora() -> Dict[str, str]:
    """Generates files, computes checksums, and records manifests."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    training_text, held_out_text = generate_expanded_seed_corpus()

    train_file = RAW_DIR / "seed_corpus.txt"
    eval_file = RAW_DIR / "held_out_eval.txt"
    manifest_file = MANIFESTS_DIR / "seed_corpus_manifest.json"

    with open(train_file, "w", encoding="utf-8") as f:
        f.write(training_text)

    with open(eval_file, "w", encoding="utf-8") as f:
        f.write(held_out_text)

    train_hash = hashlib.sha256(training_text.encode("utf-8")).hexdigest()
    eval_hash = hashlib.sha256(held_out_text.encode("utf-8")).hexdigest()

    manifest = {
        "dataset_name": "love_native_tokenizer_seed_corpus",
        "version": "1.0.0",
        "license": "Creative Commons Zero 1.0 (CC0) / Dedicated Public Domain",
        "provenance": "Synthetically curated domain-specific technical prose and dialogues authored for LOVE Native AI",
        "contains_pii": False,
        "contains_private_memories": False,
        "language": "en",
        "training_file": str(train_file.name),
        "training_file_bytes": len(training_text.encode("utf-8")),
        "training_file_characters": len(training_text),
        "training_file_sha256": train_hash,
        "evaluation_file": str(eval_file.name),
        "evaluation_file_bytes": len(held_out_text.encode("utf-8")),
        "evaluation_file_characters": len(held_out_text),
        "evaluation_file_sha256": eval_hash,
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Training corpus created: {train_file} ({manifest['training_file_bytes']:,} bytes, SHA-256: {train_hash[:12]}...)")
    print(f"Held-out eval created: {eval_file} ({manifest['evaluation_file_bytes']:,} bytes, SHA-256: {eval_hash[:12]}...)")
    print(f"Manifest recorded: {manifest_file}")

    return {
        "train_file": str(train_file),
        "eval_file": str(eval_file),
        "manifest_file": str(manifest_file),
        "train_sha256": train_hash,
        "eval_sha256": eval_hash,
    }


if __name__ == "__main__":
    build_and_save_corpora()
