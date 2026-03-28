# knowledge/bootstrap_protocol.py

"""
Accelerated Bootstrap Protocol (ABP)

Orchestrates Daedalus's self-directed learning from cold start to PhD-level
knowledge across all major academic, trade, and philosophical disciplines.

The ABP uses existing architecture — Curiosity Engine, Goal Planner, Active
Learner, LLM Adapter — at an accelerated cadence to systematically ingest,
verify, and cross-link knowledge until per-discipline benchmarks are met.

Design:
  - Curriculum is a 7-layer dependency DAG of ~40 disciplines, ~1,500 sub-domains
  - Each sub-domain has PhD-level benchmarks (entity count, link density, coherence)
  - ABP runs as a background process; operator queries always take priority
  - Verification standards are NEVER lowered — only processing speed increases
  - Trust builds slowly by design (single-source-class ceiling)
  - Graduation triggers automatic transition to normal operating cadence

Lifecycle:
  IDLE -> INITIALIZING -> CURRICULUM_GENERATED -> RUNNING -> GRADUATING -> COMPLETE

Integration:
  All operations route through integration_layer governed wrappers.
  The Meta Reasoner checks ABP status each cycle and adjusts cadence accordingly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ABPPhase(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    CURRICULUM_GENERATED = "curriculum_generated"
    RUNNING = "running"
    GRADUATING = "graduating"
    COMPLETE = "complete"


class DisciplineLayer(int, Enum):
    FOUNDATIONAL = 1
    NATURAL_SCIENCES = 2
    FORMAL_APPLIED = 3
    SOCIAL_SCIENCES = 4
    HUMANITIES = 5
    TRADES = 6
    INTERDISCIPLINARY = 7


@dataclass
class SubDomainBenchmark:
    """PhD-level graduation criteria for a single sub-domain."""
    min_verified_entities: int = 500
    min_cross_links: int = 15
    min_internal_coherence: float = 0.85
    max_contradiction_rate: float = 0.05
    min_methodology_items: int = 30
    min_frontier_items: int = 15


@dataclass
class DisciplineSpec:
    name: str
    layer: DisciplineLayer
    sub_domains: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class SubDomainProgress:
    discipline: str
    sub_domain: str
    layer: DisciplineLayer
    verified_entities: int = 0
    cross_links: int = 0
    internal_coherence: float = 0.0
    contradiction_rate: float = 0.0
    methodology_items: int = 0
    frontier_items: int = 0
    ingestion_queries: int = 0
    verification_cycles: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    is_complete: bool = False

    def meets_benchmark(self, bench: SubDomainBenchmark) -> bool:
        return (
            self.verified_entities >= bench.min_verified_entities
            and self.cross_links >= bench.min_cross_links
            and self.internal_coherence >= bench.min_internal_coherence
            and self.contradiction_rate <= bench.max_contradiction_rate
            and self.methodology_items >= bench.min_methodology_items
            and self.frontier_items >= bench.min_frontier_items
        )


# ----------------------------------------------------------------
# PhD-LEVEL CURRICULUM (7-layer DAG)
# ----------------------------------------------------------------

CURRICULUM: List[DisciplineSpec] = [
    # Layer 1: Foundational
    DisciplineSpec("Formal Logic & Critical Thinking", DisciplineLayer.FOUNDATIONAL,
                   ["Propositional Logic", "Predicate Logic", "Modal Logic",
                    "Informal Fallacies", "Argumentation Theory", "Set Theory",
                    "Proof Theory", "Computational Logic"]),
    DisciplineSpec("Mathematics", DisciplineLayer.FOUNDATIONAL,
                   ["Algebra", "Calculus & Analysis", "Number Theory", "Statistics & Probability",
                    "Topology", "Linear Algebra", "Differential Equations", "Discrete Mathematics",
                    "Abstract Algebra", "Numerical Methods", "Complex Analysis",
                    "Measure Theory", "Category Theory", "Combinatorics"]),
    DisciplineSpec("Linguistics & Language Structure", DisciplineLayer.FOUNDATIONAL,
                   ["Phonetics & Phonology", "Morphology", "Syntax", "Semantics",
                    "Pragmatics", "Sociolinguistics", "Psycholinguistics",
                    "Computational Linguistics", "Historical Linguistics"]),
    DisciplineSpec("Epistemology", DisciplineLayer.FOUNDATIONAL,
                   ["Theory of Knowledge", "Justification & Belief", "Scientific Method",
                    "Philosophy of Science", "Bayesian Epistemology",
                    "Social Epistemology", "Formal Epistemology"]),

    # Layer 2: Natural Sciences
    DisciplineSpec("Physics", DisciplineLayer.NATURAL_SCIENCES,
                   ["Classical Mechanics", "Electrodynamics", "Thermodynamics",
                    "Quantum Mechanics", "Statistical Mechanics", "General Relativity",
                    "Quantum Field Theory", "Condensed Matter", "Nuclear Physics",
                    "Plasma Physics", "Optics", "Astrophysics", "Particle Physics",
                    "Computational Physics"],
                   prerequisites=["Mathematics", "Formal Logic & Critical Thinking"]),
    DisciplineSpec("Chemistry", DisciplineLayer.NATURAL_SCIENCES,
                   ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry",
                    "Biochemistry", "Analytical Chemistry", "Quantum Chemistry",
                    "Polymer Chemistry", "Environmental Chemistry",
                    "Medicinal Chemistry", "Chemical Engineering Fundamentals"],
                   prerequisites=["Mathematics", "Physics"]),
    DisciplineSpec("Biology", DisciplineLayer.NATURAL_SCIENCES,
                   ["Molecular Biology", "Cell Biology", "Genetics", "Evolutionary Biology",
                    "Ecology", "Microbiology", "Neuroscience", "Developmental Biology",
                    "Immunology", "Bioinformatics Foundations", "Marine Biology",
                    "Botany", "Zoology"],
                   prerequisites=["Chemistry"]),
    DisciplineSpec("Earth Sciences", DisciplineLayer.NATURAL_SCIENCES,
                   ["Geology", "Meteorology", "Oceanography", "Geophysics",
                    "Paleontology", "Hydrology", "Volcanology", "Seismology",
                    "Mineralogy"],
                   prerequisites=["Physics", "Chemistry"]),
    DisciplineSpec("Astronomy & Astrophysics", DisciplineLayer.NATURAL_SCIENCES,
                   ["Observational Astronomy", "Stellar Evolution", "Cosmology",
                    "Planetary Science", "Galactic Astronomy", "Gravitational Physics",
                    "Astrobiology", "Radio Astronomy"],
                   prerequisites=["Physics", "Mathematics"]),

    # Layer 3: Formal & Applied Sciences
    DisciplineSpec("Computer Science", DisciplineLayer.FORMAL_APPLIED,
                   ["Algorithms & Data Structures", "Programming Languages",
                    "Operating Systems", "Computer Networks", "Databases",
                    "AI & Machine Learning", "Computer Security", "Distributed Systems",
                    "Computer Graphics", "Formal Verification", "Compilers",
                    "Human-Computer Interaction", "Quantum Computing",
                    "Software Engineering"],
                   prerequisites=["Mathematics", "Formal Logic & Critical Thinking"]),
    DisciplineSpec("Engineering", DisciplineLayer.FORMAL_APPLIED,
                   ["Mechanical Engineering", "Electrical Engineering",
                    "Civil Engineering", "Chemical Engineering", "Aerospace Engineering",
                    "Materials Engineering", "Biomedical Engineering",
                    "Systems Engineering", "Control Theory", "Robotics",
                    "Environmental Engineering"],
                   prerequisites=["Physics", "Mathematics", "Chemistry"]),
    DisciplineSpec("Medicine & Health Sciences", DisciplineLayer.FORMAL_APPLIED,
                   ["Anatomy & Physiology", "Pathology", "Pharmacology",
                    "Epidemiology", "Surgery Principles", "Internal Medicine",
                    "Psychiatry", "Public Health", "Medical Ethics",
                    "Diagnostic Methods", "Rehabilitation Science"],
                   prerequisites=["Biology", "Chemistry"]),
    DisciplineSpec("Materials Science", DisciplineLayer.FORMAL_APPLIED,
                   ["Crystallography", "Polymer Science", "Nanomaterials",
                    "Ceramics", "Metallurgy", "Composite Materials",
                    "Biomaterials", "Electronic Materials"],
                   prerequisites=["Physics", "Chemistry"]),

    # Layer 4: Social Sciences
    DisciplineSpec("Psychology", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Cognitive Psychology", "Developmental Psychology",
                    "Clinical Psychology", "Social Psychology", "Neuropsychology",
                    "Behavioral Psychology", "Positive Psychology",
                    "Research Methods in Psychology", "Psychometrics",
                    "Evolutionary Psychology"],
                   prerequisites=["Biology", "Mathematics"]),
    DisciplineSpec("Sociology & Anthropology", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Social Theory", "Cultural Anthropology", "Physical Anthropology",
                    "Archaeology", "Ethnography", "Urban Sociology",
                    "Sociology of Religion", "Demographic Analysis",
                    "Social Stratification"],
                   prerequisites=["Epistemology"]),
    DisciplineSpec("Economics", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Microeconomics", "Macroeconomics", "Econometrics",
                    "Behavioral Economics", "International Economics",
                    "Development Economics", "Financial Economics",
                    "Game Theory", "Labor Economics", "Public Economics"],
                   prerequisites=["Mathematics"]),
    DisciplineSpec("Political Science & Governance", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Political Theory", "Comparative Politics", "International Relations",
                    "Public Administration", "Constitutional Law",
                    "Political Economy", "Security Studies",
                    "Electoral Systems", "Policy Analysis"],
                   prerequisites=["Epistemology"]),
    DisciplineSpec("History", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Ancient History", "Medieval History", "Early Modern History",
                    "Modern History", "History of Science & Technology",
                    "Economic History", "Military History", "Historiography",
                    "Regional Studies", "Oral History Methods"],
                   prerequisites=["Epistemology"]),
    DisciplineSpec("Geography", DisciplineLayer.SOCIAL_SCIENCES,
                   ["Physical Geography", "Human Geography", "Cartography & GIS",
                    "Urban Geography", "Environmental Geography",
                    "Geopolitics", "Economic Geography"],
                   prerequisites=["Earth Sciences"]),

    # Layer 5: Humanities & Philosophy
    DisciplineSpec("Philosophy", DisciplineLayer.HUMANITIES,
                   ["Metaphysics", "Ethics", "Aesthetics", "Political Philosophy",
                    "Philosophy of Mind", "Philosophy of Language",
                    "Existentialism & Phenomenology", "Eastern Philosophy",
                    "Philosophy of Mathematics", "Applied Ethics",
                    "Logic & Formal Philosophy"],
                   prerequisites=["Epistemology", "Formal Logic & Critical Thinking"]),
    DisciplineSpec("Literature & Literary Theory", DisciplineLayer.HUMANITIES,
                   ["Literary Criticism", "Comparative Literature", "Narrative Theory",
                    "Poetry & Poetics", "Drama Studies", "Postcolonial Literature",
                    "Genre Studies", "Digital Humanities"],
                   prerequisites=["Linguistics & Language Structure"]),
    DisciplineSpec("Art History & Theory", DisciplineLayer.HUMANITIES,
                   ["Ancient & Classical Art", "Renaissance Art", "Modern Art",
                    "Contemporary Art", "Art Theory & Criticism",
                    "Architecture History", "Photography Theory",
                    "Digital Art & New Media"],
                   prerequisites=["History"]),
    DisciplineSpec("Music Theory", DisciplineLayer.HUMANITIES,
                   ["Harmony & Counterpoint", "Rhythm & Meter", "Musical Form",
                    "Orchestration", "Ethnomusicology", "Music Cognition",
                    "Electronic Music Theory", "Music History"],
                   prerequisites=["Mathematics"]),
    DisciplineSpec("Religious Studies", DisciplineLayer.HUMANITIES,
                   ["Comparative Religion", "Theology", "Religious History",
                    "Philosophy of Religion", "Mysticism", "Religious Ethics",
                    "Sociology of Religion", "Sacred Texts"],
                   prerequisites=["History", "Philosophy"]),
    DisciplineSpec("Law & Jurisprudence", DisciplineLayer.HUMANITIES,
                   ["Legal Theory", "Constitutional Law", "International Law",
                    "Criminal Law", "Contract Law", "Human Rights Law",
                    "Environmental Law", "Intellectual Property",
                    "Legal Ethics", "Comparative Legal Systems"],
                   prerequisites=["Political Science & Governance", "Philosophy"]),

    # Layer 6: Trade & Applied Knowledge
    DisciplineSpec("Construction & Building Trades", DisciplineLayer.TRADES,
                   ["Structural Principles", "Electrical Systems", "Plumbing & HVAC",
                    "Carpentry & Woodworking", "Masonry", "Project Management",
                    "Building Codes & Safety", "Green Building"],
                   prerequisites=["Engineering"]),
    DisciplineSpec("Manufacturing & Industrial Processes", DisciplineLayer.TRADES,
                   ["CNC Machining", "Welding & Fabrication", "Quality Control",
                    "Lean Manufacturing", "Supply Chain Management",
                    "Industrial Automation", "Additive Manufacturing"],
                   prerequisites=["Engineering", "Materials Science"]),
    DisciplineSpec("Agriculture & Food Science", DisciplineLayer.TRADES,
                   ["Crop Science", "Animal Husbandry", "Soil Science",
                    "Food Technology", "Agricultural Economics",
                    "Sustainable Agriculture", "Aquaculture",
                    "Food Safety & Regulation"],
                   prerequisites=["Biology", "Chemistry"]),
    DisciplineSpec("Information Technology", DisciplineLayer.TRADES,
                   ["Systems Administration", "Network Engineering",
                    "Cloud Computing", "DevOps", "IT Security",
                    "Database Administration", "IT Service Management"],
                   prerequisites=["Computer Science"]),
    DisciplineSpec("Financial Services", DisciplineLayer.TRADES,
                   ["Accounting", "Financial Analysis", "Banking",
                    "Insurance", "Investment Management", "Tax Law",
                    "Auditing", "Financial Regulation"],
                   prerequisites=["Economics"]),
    DisciplineSpec("Healthcare Practice", DisciplineLayer.TRADES,
                   ["Nursing", "Paramedicine", "Pharmacy Practice",
                    "Physical Therapy", "Occupational Therapy",
                    "Medical Laboratory Science", "Health Informatics"],
                   prerequisites=["Medicine & Health Sciences"]),

    # Layer 7: Interdisciplinary & Emerging
    DisciplineSpec("Cognitive Science", DisciplineLayer.INTERDISCIPLINARY,
                   ["Neural Computation", "Cognitive Architectures",
                    "Language & Thought", "Perception & Action",
                    "Decision Making", "Consciousness Studies",
                    "Embodied Cognition"],
                   prerequisites=["Psychology", "Computer Science", "Philosophy"]),
    DisciplineSpec("Bioinformatics", DisciplineLayer.INTERDISCIPLINARY,
                   ["Sequence Analysis", "Structural Bioinformatics",
                    "Genomics", "Proteomics", "Systems Biology",
                    "Computational Drug Design"],
                   prerequisites=["Biology", "Computer Science"]),
    DisciplineSpec("Climate Science", DisciplineLayer.INTERDISCIPLINARY,
                   ["Climate Modeling", "Paleoclimatology", "Atmospheric Chemistry",
                    "Climate Policy", "Carbon Cycle", "Climate Adaptation"],
                   prerequisites=["Earth Sciences", "Physics"]),
    DisciplineSpec("Data Science & Analytics", DisciplineLayer.INTERDISCIPLINARY,
                   ["Statistical Learning", "Data Engineering",
                    "Visualization", "Natural Language Processing",
                    "Time Series Analysis", "Causal Inference",
                    "Ethics of Data"],
                   prerequisites=["Mathematics", "Computer Science"]),
    DisciplineSpec("Ethics of Technology & AI", DisciplineLayer.INTERDISCIPLINARY,
                   ["AI Ethics", "Algorithmic Fairness", "Privacy & Surveillance",
                    "Digital Rights", "Autonomous Systems Ethics",
                    "Technology & Society", "Responsible Innovation"],
                   prerequisites=["Philosophy", "Computer Science"]),
    DisciplineSpec("Systems Theory & Complexity", DisciplineLayer.INTERDISCIPLINARY,
                   ["General Systems Theory", "Complex Adaptive Systems",
                    "Network Science", "Chaos Theory", "Emergence",
                    "Agent-Based Modeling", "Cybernetics"],
                   prerequisites=["Mathematics", "Physics"]),
]


# ----------------------------------------------------------------
# GLOBAL BENCHMARKS
# ----------------------------------------------------------------

PHD_BENCHMARK = SubDomainBenchmark(
    min_verified_entities=500,
    min_cross_links=15,
    min_internal_coherence=0.85,
    max_contradiction_rate=0.05,
    min_methodology_items=30,
    min_frontier_items=15,
)

GLOBAL_GRADUATION = {
    "min_coherence": 0.85,
    "min_stability": 0.90,
    "min_quality": 0.93,
    "min_breadth_coverage": 0.95,
    "min_avg_reasoning_depth": 5,
    "min_contradiction_resolution_rate": 0.95,
    "min_avg_cross_links": 15,
}


# ----------------------------------------------------------------
# ABP ORCHESTRATOR
# ----------------------------------------------------------------

class BootstrapProtocol:
    """
    Orchestrates the Accelerated Bootstrap Protocol lifecycle.

    The orchestrator does NOT perform ingestion itself — it generates
    structured learning goals and delegates to the existing Curiosity
    Engine, Goal Planner, Active Learner, and LLM Adapter.
    """

    def __init__(self) -> None:
        self.phase: ABPPhase = ABPPhase.IDLE
        self.started_at: float = 0.0
        self.graduated_at: float = 0.0
        self.current_layer: DisciplineLayer = DisciplineLayer.FOUNDATIONAL
        self.progress: Dict[str, SubDomainProgress] = {}
        self.total_disciplines: int = len(CURRICULUM)
        self.total_sub_domains: int = sum(len(d.sub_domains) for d in CURRICULUM)
        self.completed_sub_domains: int = 0
        self.total_ingestion_queries: int = 0
        self.cadence_multiplier: float = 1.0
        self._staleness_grace_until: float = 0.0

    def start(self) -> Dict[str, Any]:
        """Initialize the ABP and generate curriculum."""
        if self.phase not in (ABPPhase.IDLE, ABPPhase.COMPLETE):
            return {"error": "ABP already running", "phase": self.phase.value}

        self.phase = ABPPhase.INITIALIZING
        self.started_at = time.time()
        self.cadence_multiplier = 4.0
        self._staleness_grace_until = self.started_at + (90 * 24 * 3600)

        self._generate_curriculum()

        self.phase = ABPPhase.RUNNING
        return {
            "phase": self.phase.value,
            "disciplines": self.total_disciplines,
            "sub_domains": self.total_sub_domains,
            "cadence_multiplier": self.cadence_multiplier,
        }

    def _generate_curriculum(self) -> None:
        """Create progress trackers for all sub-domains."""
        self.progress = {}
        for disc in CURRICULUM:
            for sub in disc.sub_domains:
                key = f"{disc.name}::{sub}"
                self.progress[key] = SubDomainProgress(
                    discipline=disc.name,
                    sub_domain=sub,
                    layer=disc.layer,
                )
        self.phase = ABPPhase.CURRICULUM_GENERATED

    def get_next_learning_targets(self, max_targets: int = 5) -> List[Dict[str, Any]]:
        """
        Return the next sub-domains to learn, respecting the dependency DAG.
        Only returns targets from layers whose prerequisites are satisfied.
        """
        if self.phase != ABPPhase.RUNNING:
            return []

        completed_disciplines = self._completed_disciplines()
        targets = []

        for disc in CURRICULUM:
            prereqs_met = all(p in completed_disciplines for p in disc.prerequisites)
            if not prereqs_met:
                continue

            for sub in disc.sub_domains:
                key = f"{disc.name}::{sub}"
                prog = self.progress.get(key)
                if prog and not prog.is_complete:
                    targets.append({
                        "key": key,
                        "discipline": disc.name,
                        "sub_domain": sub,
                        "layer": disc.layer.value,
                        "progress": prog,
                    })
                    if len(targets) >= max_targets:
                        return targets

        return targets

    def _completed_disciplines(self) -> set:
        """Disciplines where all sub-domains meet PhD benchmark."""
        completed = set()
        for disc in CURRICULUM:
            all_done = True
            for sub in disc.sub_domains:
                key = f"{disc.name}::{sub}"
                prog = self.progress.get(key)
                if not prog or not prog.is_complete:
                    all_done = False
                    break
            if all_done:
                completed.add(disc.name)
        return completed

    def record_progress(
        self,
        key: str,
        entities_added: int = 0,
        links_added: int = 0,
        methodology_added: int = 0,
        frontier_added: int = 0,
        coherence: float = 0.0,
        contradiction_rate: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Update sub-domain progress and check benchmark."""
        prog = self.progress.get(key)
        if not prog:
            return None

        prog.verified_entities += entities_added
        prog.cross_links += links_added
        prog.methodology_items += methodology_added
        prog.frontier_items += frontier_added
        prog.internal_coherence = coherence
        prog.contradiction_rate = contradiction_rate
        prog.ingestion_queries += 1
        self.total_ingestion_queries += 1

        if not prog.is_complete and prog.meets_benchmark(PHD_BENCHMARK):
            prog.is_complete = True
            prog.completed_at = time.time()
            self.completed_sub_domains += 1
            self._update_current_layer()
            return {"graduated": True, "key": key,
                    "sub_domain": prog.sub_domain,
                    "discipline": prog.discipline}

        return {"graduated": False, "key": key}

    def _update_current_layer(self) -> None:
        """Recompute current_layer from incomplete sub-domains."""
        active_layers = set()
        for disc in CURRICULUM:
            for sub in disc.sub_domains:
                key = f"{disc.name}::{sub}"
                prog = self.progress.get(key)
                if not prog or not prog.is_complete:
                    active_layers.add(disc.layer)
                    break
        if active_layers:
            self.current_layer = min(active_layers, key=lambda l: l.value)

    def check_global_graduation(self, system_metrics: Dict[str, float]) -> bool:
        """Check if global graduation criteria are met."""
        if self.phase != ABPPhase.RUNNING:
            return False

        breadth = self.completed_sub_domains / max(1, self.total_sub_domains)
        if breadth < GLOBAL_GRADUATION["min_breadth_coverage"]:
            return False

        coherence = system_metrics.get("coherence", 0)
        stability = system_metrics.get("stability", 0)
        quality = system_metrics.get("quality", 0)

        return (
            coherence >= GLOBAL_GRADUATION["min_coherence"]
            and stability >= GLOBAL_GRADUATION["min_stability"]
            and quality >= GLOBAL_GRADUATION["min_quality"]
        )

    def graduate(self) -> Dict[str, Any]:
        """Transition from ABP to normal operating mode."""
        self.phase = ABPPhase.COMPLETE
        self.graduated_at = time.time()
        self.cadence_multiplier = 1.0
        elapsed = self.graduated_at - self.started_at
        return {
            "phase": self.phase.value,
            "elapsed_seconds": elapsed,
            "elapsed_days": elapsed / 86400,
            "sub_domains_completed": self.completed_sub_domains,
            "total_sub_domains": self.total_sub_domains,
            "total_ingestion_queries": self.total_ingestion_queries,
        }

    def is_staleness_grace_active(self) -> bool:
        """During ABP, new items get a 90-day staleness grace period."""
        if self.phase != ABPPhase.RUNNING:
            return False
        return time.time() < self._staleness_grace_until

    def status(self) -> Dict[str, Any]:
        completed_disc = len(self._completed_disciplines())
        return {
            "phase": self.phase.value,
            "disciplines_total": self.total_disciplines,
            "disciplines_completed": completed_disc,
            "sub_domains_total": self.total_sub_domains,
            "sub_domains_completed": self.completed_sub_domains,
            "breadth_coverage": round(
                self.completed_sub_domains / max(1, self.total_sub_domains), 4),
            "cadence_multiplier": self.cadence_multiplier,
            "staleness_grace_active": self.is_staleness_grace_active(),
            "total_ingestion_queries": self.total_ingestion_queries,
            "current_layer": self.current_layer.value
                if self.phase == ABPPhase.RUNNING else None,
            "started_at": self.started_at,
            "graduated_at": self.graduated_at,
        }


# ----------------------------------------------------------------
# GLOBAL INSTANCE
# ----------------------------------------------------------------

_bootstrap = BootstrapProtocol()


def get_bootstrap() -> BootstrapProtocol:
    return _bootstrap


def start_bootstrap() -> Dict[str, Any]:
    return _bootstrap.start()


def bootstrap_status() -> Dict[str, Any]:
    return _bootstrap.status()


def is_abp_active() -> bool:
    return _bootstrap.phase == ABPPhase.RUNNING
