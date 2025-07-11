"""
Enhanced memory categorization system for autonomous AI memory storage.
This module provides advanced categorization logic optimized for coding contexts.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict
import json

from mem0.configs.coding_config import CodingMemoryConfig

logger = logging.getLogger(__name__)


class HierarchicalCategorizer:
    """
    Hierarchical categorization system for autonomous AI memory storage.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.coding_config = CodingMemoryConfig()

        # Hierarchical category structure
        self.category_hierarchy = {
            "development": {
                "code_implementation": [
                    "functions",
                    "classes",
                    "modules",
                    "algorithms",
                ],
                "architecture": ["patterns", "design", "structure", "frameworks"],
                "testing": [
                    "unit_tests",
                    "integration_tests",
                    "e2e_tests",
                    "test_strategies",
                ],
                "refactoring": [
                    "code_cleanup",
                    "optimization",
                    "restructuring",
                    "modernization",
                ],
            },
            "troubleshooting": {
                "bug_fix": [
                    "syntax_errors",
                    "logic_errors",
                    "runtime_errors",
                    "edge_cases",
                ],
                "debugging": ["techniques", "tools", "strategies", "investigation"],
                "error_solution": ["fixes", "workarounds", "patches", "root_causes"],
                "performance": ["bottlenecks", "optimization", "profiling", "scaling"],
            },
            "operations": {
                "deployment": [
                    "ci_cd",
                    "containerization",
                    "orchestration",
                    "environments",
                ],
                "configuration": [
                    "settings",
                    "environment_vars",
                    "parameters",
                    "secrets",
                ],
                "monitoring": ["logging", "metrics", "alerting", "observability"],
                "maintenance": ["updates", "patches", "cleanup", "migrations"],
            },
            "knowledge": {
                "documentation": ["api_docs", "readme", "guides", "examples"],
                "learning": ["concepts", "patterns", "best_practices", "tutorials"],
                "reference": ["libraries", "frameworks", "tools", "resources"],
            },
        }

        # Category detection patterns
        self.detection_patterns = {
            "code_implementation": [
                r"\bdef\s+\w+\(",
                r"\bclass\s+\w+",
                r"\bfunction\s+\w+",
                r"\bimport\s+\w+",
                r"\bfrom\s+\w+\s+import",
                r"\b(algorithm|implementation|code|function|method)\b",
            ],
            "bug_fix": [
                r"\b(bug|fix|error|issue|problem|fault)\b",
                r"\b(broken|crashed|failed|exception)\b",
                r"\b(traceback|stack trace)\b",
            ],
            "error_solution": [
                r"\b(solution|solve|resolved|answer|fix)\b",
                r"\b(workaround|patch|repair|correct)\b",
                r"\b(resolved|fixed|solved)\b",
            ],
            "performance": [
                r"\b(performance|speed|optimize|faster|slow)\b",
                r"\b(bottleneck|efficiency|latency|throughput)\b",
                r"\b(memory|cpu|resource|benchmark)\b",
            ],
            "testing": [
                r"\b(test|testing|spec|assert|expect)\b",
                r"\b(unit test|integration test|e2e|pytest|jest)\b",
                r"\b(coverage|mock|fixture|stub)\b",
            ],
            "debugging": [
                r"\b(debug|debugger|breakpoint|inspect)\b",
                r"\b(trace|log|print|console)\b",
                r"\b(investigate|analyze|examine)\b",
            ],
            "architecture": [
                r"\b(architecture|design|pattern|structure)\b",
                r"\b(mvc|mvp|mvvm|microservice|monolith)\b",
                r"\b(framework|library|component|module)\b",
            ],
            "deployment": [
                r"\b(deploy|deployment|ci|cd|pipeline)\b",
                r"\b(docker|kubernetes|container|orchestration)\b",
                r"\b(environment|staging|production|release)\b",
            ],
            "configuration": [
                r"\b(config|configuration|setting|parameter)\b",
                r"\b(env|environment|variable|secret)\b",
                r"\b(property|option|preference)\b",
            ],
            "documentation": [
                r"\b(document|documentation|readme|guide)\b",
                r"\b(api doc|manual|tutorial|example)\b",
                r"\b(comment|docstring|annotation)\b",
            ],
            "refactoring": [
                r"\b(refactor|refactoring|cleanup|restructure)\b",
                r"\b(improve|enhance|optimize|modernize)\b",
                r"\b(rewrite|reorganize|simplify)\b",
            ],
        }

        # File extension mappings
        self.file_extension_categories = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c_header",
            ".hpp": "cpp_header",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "bash",
            ".zsh": "zsh",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".md": "markdown",
            ".txt": "text",
            ".log": "log",
            ".config": "config",
            ".env": "environment",
        }

        # Category confidence weights
        self.category_confidence = {
            "bug_fix": 0.9,
            "error_solution": 0.95,
            "performance": 0.85,
            "testing": 0.8,
            "debugging": 0.85,
            "architecture": 0.8,
            "deployment": 0.82,
            "configuration": 0.88,
            "documentation": 0.75,
            "refactoring": 0.78,
            "code_implementation": 0.83,
        }

        # Category statistics
        self.category_stats = defaultdict(int)
        self.categorization_history = []

        logger.info("Hierarchical categorizer initialized")

    def categorize_memory(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Categorize memory content with hierarchical organization.

        Args:
            memory_content: The memory content to categorize
            metadata: Memory metadata
            context: Optional context for categorization

        Returns:
            Dictionary containing category information
        """
        context = context or {}

        # Auto-detect primary category
        primary_category = self._detect_primary_category(memory_content, metadata)

        # Determine sub-categories
        sub_categories = self._determine_sub_categories(
            memory_content, metadata, primary_category
        )

        # Extract technology tags
        technology_tags = self._extract_technology_tags(memory_content, metadata)

        # Calculate confidence
        confidence = self._calculate_categorization_confidence(
            memory_content, metadata, primary_category
        )

        # Build hierarchical path
        hierarchical_path = self._build_hierarchical_path(
            primary_category, sub_categories, technology_tags
        )

        # Record categorization
        self._record_categorization(primary_category, sub_categories, confidence)

        return {
            "primary_category": primary_category,
            "sub_categories": sub_categories,
            "technology_tags": technology_tags,
            "hierarchical_path": hierarchical_path,
            "confidence": confidence,
            "explanation": self._generate_categorization_explanation(
                primary_category, sub_categories, confidence
            ),
        }

    def _detect_primary_category(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Detect primary category using pattern matching and context clues.
        """
        content_lower = content.lower()

        # Check for explicit category hints in metadata
        if metadata.get("category"):
            explicit_category = metadata["category"]
            if explicit_category in self.detection_patterns:
                return explicit_category

        # Pattern-based detection
        category_scores = {}

        for category, patterns in self.detection_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches

            if score > 0:
                category_scores[category] = score

        # File extension hints
        file_refs = metadata.get("file_references", [])
        if file_refs:
            for file_ref in file_refs:
                for ext, file_type in self.file_extension_categories.items():
                    if file_ref.endswith(ext):
                        # Boost relevant categories based on file type
                        if file_type in ["python", "javascript", "java"]:
                            category_scores["code_implementation"] = (
                                category_scores.get("code_implementation", 0) + 2
                            )
                        elif file_type == "config":
                            category_scores["configuration"] = (
                                category_scores.get("configuration", 0) + 3
                            )
                        elif file_type == "markdown":
                            category_scores["documentation"] = (
                                category_scores.get("documentation", 0) + 2
                            )

        # Context-based hints
        if metadata.get("error_related", False):
            category_scores["bug_fix"] = category_scores.get("bug_fix", 0) + 3

        if metadata.get("solution_related", False):
            category_scores["error_solution"] = (
                category_scores.get("error_solution", 0) + 3
            )

        # Return category with highest score
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return "code_implementation"  # Default category

    def _determine_sub_categories(
        self, content: str, metadata: Dict[str, Any], primary_category: str
    ) -> List[str]:
        """
        Determine sub-categories based on hierarchical structure.
        """
        sub_categories = []

        # Find primary category in hierarchy
        for main_category, sub_cats in self.category_hierarchy.items():
            if primary_category in sub_cats:
                # Check for sub-category patterns
                content_lower = content.lower()
                available_subs = sub_cats[primary_category]

                for sub_cat in available_subs:
                    sub_patterns = self._get_sub_category_patterns(sub_cat)
                    for pattern in sub_patterns:
                        if re.search(pattern, content_lower, re.IGNORECASE):
                            sub_categories.append(sub_cat)
                            break
                break

        return list(set(sub_categories))  # Remove duplicates

    def _get_sub_category_patterns(self, sub_category: str) -> List[str]:
        """
        Get patterns for detecting sub-categories.
        """
        patterns = {
            "functions": [r"\bdef\s+\w+\(", r"\bfunction\s+\w+", r"\bmethod\b"],
            "classes": [r"\bclass\s+\w+", r"\bobject\s+oriented", r"\binheritance\b"],
            "modules": [r"\bmodule\b", r"\bpackage\b", r"\bimport\b"],
            "algorithms": [
                r"\balgorithm\b",
                r"\bsort\b",
                r"\bsearch\b",
                r"\boptimize\b",
            ],
            "patterns": [
                r"\bpattern\b",
                r"\bsingleton\b",
                r"\bfactory\b",
                r"\bobserver\b",
            ],
            "design": [r"\bdesign\b", r"\barchitecture\b", r"\bstructure\b"],
            "unit_tests": [r"\bunit\s+test\b", r"\bunittest\b", r"\bpytest\b"],
            "integration_tests": [r"\bintegration\s+test\b", r"\bapi\s+test\b"],
            "syntax_errors": [
                r"\bsyntax\s+error\b",
                r"\bindentation\b",
                r"\bparsing\b",
            ],
            "logic_errors": [r"\ologic\s+error\b", r"\balgorithm\s+bug\b"],
            "runtime_errors": [r"\bruntime\s+error\b", r"\bexception\b", r"\bcrash\b"],
            "techniques": [r"\btechnique\b", r"\bmethod\b", r"\bapproach\b"],
            "tools": [r"\btool\b", r"\bdebugger\b", r"\bprofiler\b"],
            "bottlenecks": [r"\bbottleneck\b", r"\bperformance\s+issue\b"],
            "optimization": [r"\boptimization\b", r"\boptimize\b", r"\bspeed\s+up\b"],
            "ci_cd": [r"\bci\b", r"\bcd\b", r"\bpipeline\b", r"\bjenkins\b"],
            "containerization": [r"\bdocker\b", r"\bcontainer\b", r"\bkubernetes\b"],
            "logging": [r"\blog\b", r"\blogging\b", r"\blogger\b"],
            "metrics": [r"\bmetric\b", r"\bmonitoring\b", r"\btelemetry\b"],
            "api_docs": [r"\bapi\s+doc\b", r"\bswagger\b", r"\bopenapi\b"],
            "readme": [r"\breadme\b", r"\bdocumentation\b"],
            "concepts": [r"\bconcept\b", r"\btheory\b", r"\bprinciple\b"],
            "best_practices": [
                r"\bbest\s+practice\b",
                r"\bconvention\b",
                r"\bstandard\b",
            ],
        }

        return patterns.get(sub_category, [sub_category.replace("_", r"\s+")])

    def _extract_technology_tags(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Extract technology tags from content and metadata.
        """
        tags = set()
        content_lower = content.lower()

        # Programming languages
        languages = {
            "python": [r"\bpython\b", r"\bpy\b", r"\.py\b", r"\bpip\b", r"\bpytest\b"],
            "javascript": [
                r"\bjavascript\b",
                r"\bjs\b",
                r"\.js\b",
                r"\bnpm\b",
                r"\bnode\b",
            ],
            "typescript": [r"\btypescript\b", r"\bts\b", r"\.ts\b", r"\btsc\b"],
            "java": [r"\bjava\b", r"\.java\b", r"\bmaven\b", r"\bgradle\b"],
            "cpp": [r"\bc\+\+\b", r"\bcpp\b", r"\.cpp\b", r"\bg\+\+\b"],
            "c": [r"\bc\b", r"\.c\b", r"\bgcc\b"],
            "go": [r"\bgolang\b", r"\bgo\b", r"\.go\b"],
            "rust": [r"\brust\b", r"\.rs\b", r"\bcargo\b"],
            "php": [r"\bphp\b", r"\.php\b"],
            "ruby": [r"\bruby\b", r"\.rb\b", r"\bgem\b"],
            "swift": [r"\bswift\b", r"\.swift\b"],
            "kotlin": [r"\bkotlin\b", r"\.kt\b"],
            "scala": [r"\bscala\b", r"\.scala\b"],
            "r": [r"\br\b", r"\.r\b"],
            "sql": [r"\bsql\b", r"\.sql\b", r"\bmysql\b", r"\bpostgres\b"],
        }

        # Frameworks and libraries
        frameworks = {
            "react": [r"\breact\b", r"\bjsx\b", r"\breact\s+native\b"],
            "vue": [r"\bvue\b", r"\bvuejs\b"],
            "angular": [r"\bangular\b", r"\bangularjs\b"],
            "express": [r"\bexpress\b", r"\bexpress\.js\b"],
            "fastapi": [r"\bfastapi\b", r"\bfast\s+api\b"],
            "django": [r"\bdjango\b"],
            "flask": [r"\bflask\b"],
            "spring": [r"\bspring\b", r"\bspring\s+boot\b"],
            "nodejs": [r"\bnode\.js\b", r"\bnodejs\b"],
            "docker": [r"\bdocker\b", r"\bcontainer\b"],
            "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
            "aws": [r"\baws\b", r"\bamazon\s+web\s+services\b"],
            "gcp": [r"\bgcp\b", r"\bgoogle\s+cloud\b"],
            "azure": [r"\bazure\b", r"\bmicrosoft\s+azure\b"],
        }

        # Check for language tags
        for lang, patterns in languages.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    tags.add(lang)
                    break

        # Check for framework tags
        for framework, patterns in frameworks.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    tags.add(framework)
                    break

        # Extract from file references
        file_refs = metadata.get("file_references", [])
        for file_ref in file_refs:
            for ext, file_type in self.file_extension_categories.items():
                if file_ref.endswith(ext):
                    tags.add(file_type)

        return list(tags)

    def _calculate_categorization_confidence(
        self, content: str, metadata: Dict[str, Any], primary_category: str
    ) -> float:
        """
        Calculate confidence in categorization decision.
        """
        base_confidence = self.category_confidence.get(primary_category, 0.8)

        # Adjust based on content quality
        content_length = len(content)
        if content_length < 20:
            base_confidence *= 0.7  # Lower confidence for short content
        elif content_length > 200:
            base_confidence *= 1.1  # Higher confidence for detailed content

        # Adjust based on metadata richness
        if metadata.get("file_references"):
            base_confidence *= 1.05

        if metadata.get("error_related", False) or metadata.get(
            "solution_related", False
        ):
            base_confidence *= 1.1

        # Adjust based on pattern strength
        content_lower = content.lower()
        pattern_matches = 0
        if primary_category in self.detection_patterns:
            for pattern in self.detection_patterns[primary_category]:
                pattern_matches += len(
                    re.findall(pattern, content_lower, re.IGNORECASE)
                )

        if pattern_matches > 3:
            base_confidence *= 1.15
        elif pattern_matches == 0:
            base_confidence *= 0.8

        return min(base_confidence, 1.0)

    def _build_hierarchical_path(
        self,
        primary_category: str,
        sub_categories: List[str],
        technology_tags: List[str],
    ) -> str:
        """
        Build hierarchical path for the categorized memory.
        """
        # Find the main category
        main_category = None
        for main_cat, sub_cats in self.category_hierarchy.items():
            if primary_category in sub_cats:
                main_category = main_cat
                break

        if not main_category:
            main_category = "general"

        # Build path
        path_parts = [main_category, primary_category]

        # Add sub-categories
        if sub_categories:
            path_parts.extend(sub_categories[:2])  # Limit to 2 sub-categories

        # Add primary technology tag
        if technology_tags:
            path_parts.append(technology_tags[0])

        return "/".join(path_parts)

    def _record_categorization(
        self, primary_category: str, sub_categories: List[str], confidence: float
    ):
        """
        Record categorization for analytics and improvement.
        """
        self.category_stats[primary_category] += 1

        self.categorization_history.append(
            {
                "primary_category": primary_category,
                "sub_categories": sub_categories,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep only recent history
        if len(self.categorization_history) > 1000:
            self.categorization_history = self.categorization_history[-1000:]

    def _generate_categorization_explanation(
        self, primary_category: str, sub_categories: List[str], confidence: float
    ) -> str:
        """
        Generate human-readable explanation for categorization.
        """
        explanation = (
            f"Categorized as '{primary_category}' with {confidence:.2f} confidence"
        )

        if sub_categories:
            explanation += f", sub-categories: {', '.join(sub_categories)}"

        return explanation

    def get_category_statistics(self) -> Dict[str, Any]:
        """
        Get categorization statistics.
        """
        total_categorizations = sum(self.category_stats.values())

        return {
            "total_categorizations": total_categorizations,
            "category_distribution": dict(self.category_stats),
            "category_percentages": (
                {
                    cat: (count / total_categorizations) * 100
                    for cat, count in self.category_stats.items()
                }
                if total_categorizations > 0
                else {}
            ),
            "hierarchy_structure": self.category_hierarchy,
            "average_confidence": (
                sum(h["confidence"] for h in self.categorization_history)
                / len(self.categorization_history)
                if self.categorization_history
                else 0.0
            ),
        }

    def suggest_categories(self, partial_content: str) -> List[Dict[str, Any]]:
        """
        Suggest categories for partial content.
        """
        suggestions = []
        content_lower = partial_content.lower()

        for category, patterns in self.detection_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches

            if score > 0:
                suggestions.append(
                    {
                        "category": category,
                        "score": score,
                        "confidence": self.category_confidence.get(category, 0.8)
                        * (score / 10),
                    }
                )

        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:5]  # Return top 5 suggestions

    def update_category_patterns(self, category: str, new_patterns: List[str]):
        """
        Update detection patterns for a category.
        """
        if category in self.detection_patterns:
            self.detection_patterns[category].extend(new_patterns)
            logger.info(f"Updated patterns for category '{category}'")
        else:
            logger.warning(f"Category '{category}' not found in detection patterns")

    def reset_statistics(self):
        """
        Reset categorization statistics.
        """
        self.category_stats.clear()
        self.categorization_history.clear()
        logger.info("Categorization statistics reset")


class AutoCategorizer:
    """
    Auto-categorization system for autonomous AI agents.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hierarchical_categorizer = HierarchicalCategorizer(config)

        # Learning parameters
        self.learning_enabled = config.get("enable_learning", True)
        self.feedback_history = []
        self.category_accuracy = defaultdict(float)

        # Auto-categorization rules
        self.auto_rules = {
            "high_confidence_threshold": 0.9,
            "medium_confidence_threshold": 0.7,
            "auto_categorize_above": 0.8,
            "require_review_below": 0.6,
        }

    def auto_categorize(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Automatically categorize memory with confidence-based decisions.
        """
        # Get categorization result
        result = self.hierarchical_categorizer.categorize_memory(
            memory_content, metadata, context
        )

        # Make auto-categorization decision
        confidence = result["confidence"]

        if confidence >= self.auto_rules["auto_categorize_above"]:
            action = "auto_categorize"
            result["auto_action"] = action
            result["requires_review"] = False
        elif confidence >= self.auto_rules["require_review_below"]:
            action = "suggest_with_review"
            result["auto_action"] = action
            result["requires_review"] = True
        else:
            action = "manual_categorization"
            result["auto_action"] = action
            result["requires_review"] = True
            result["suggestions"] = self.hierarchical_categorizer.suggest_categories(
                memory_content
            )

        # Record decision
        self._record_auto_decision(result, context)

        return result

    def _record_auto_decision(self, result: Dict[str, Any], context: Dict[str, Any]):
        """
        Record auto-categorization decision for learning.
        """
        if self.learning_enabled:
            decision_record = {
                "primary_category": result["primary_category"],
                "confidence": result["confidence"],
                "action": result["auto_action"],
                "timestamp": datetime.now().isoformat(),
                "context": context.copy() if context else {},
            }

            self.feedback_history.append(decision_record)

            # Keep only recent history
            if len(self.feedback_history) > 1000:
                self.feedback_history = self.feedback_history[-1000:]

    def provide_feedback(
        self, memory_id: str, correct_category: str, was_correct: bool
    ):
        """
        Provide feedback for learning and improvement.
        """
        if was_correct:
            self.category_accuracy[correct_category] += 1
        else:
            self.category_accuracy[correct_category] -= 1

        # Adjust confidence thresholds based on feedback
        if self.learning_enabled:
            self._adjust_thresholds_based_on_feedback()

        logger.info(
            f"Feedback recorded for memory {memory_id}: {'correct' if was_correct else 'incorrect'}"
        )

    def _adjust_thresholds_based_on_feedback(self):
        """
        Adjust auto-categorization thresholds based on feedback.
        """
        # Calculate overall accuracy
        total_feedback = sum(abs(acc) for acc in self.category_accuracy.values())
        if total_feedback < 10:  # Need minimum feedback
            return

        positive_feedback = sum(
            acc for acc in self.category_accuracy.values() if acc > 0
        )
        accuracy_rate = positive_feedback / total_feedback

        # Adjust thresholds
        if accuracy_rate > 0.9:
            # High accuracy, can be more aggressive
            self.auto_rules["auto_categorize_above"] = max(
                self.auto_rules["auto_categorize_above"] - 0.05, 0.7
            )
        elif accuracy_rate < 0.7:
            # Low accuracy, be more conservative
            self.auto_rules["auto_categorize_above"] = min(
                self.auto_rules["auto_categorize_above"] + 0.05, 0.95
            )

        logger.info(
            f"Adjusted auto-categorization thresholds based on accuracy: {accuracy_rate:.3f}"
        )

    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get learning and performance statistics.
        """
        return {
            "learning_enabled": self.learning_enabled,
            "feedback_count": len(self.feedback_history),
            "category_accuracy": dict(self.category_accuracy),
            "current_thresholds": self.auto_rules,
            "recent_decisions": (
                self.feedback_history[-10:] if self.feedback_history else []
            ),
        }

    def reset_learning_data(self):
        """
        Reset learning data.
        """
        self.feedback_history.clear()
        self.category_accuracy.clear()
        logger.info("Auto-categorization learning data reset")
