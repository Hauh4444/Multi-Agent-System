"""
Pytest configuration and fixtures.
"""

import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.genai.types")
warnings.filterwarnings("ignore", message=".*PydanticDeprecatedSince212.*")
warnings.filterwarnings("ignore", message=".*model_validator.*mode.*after.*")
warnings.filterwarnings("ignore", message=".*Using.*model_validator.*with.*mode.*after.*")

# Suppress all deprecation warnings from google.genai
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.genai")
