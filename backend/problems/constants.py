"""Shared bounds for problem limits and tags.

MIN_MEMORY_LIMIT_MB is derived from the judge executor: jvm_heap =
max(memory_limit_mb - 64, 32). Values below 96 MB give the JVM a heap
larger than the container mem_limit and guarantee OOM kills.
"""

MIN_TIME_LIMIT_MS = 100
MAX_TIME_LIMIT_MS = 30_000

MIN_MEMORY_LIMIT_MB = 96
MAX_MEMORY_LIMIT_MB = 2048

MAX_TAGS = 12
MAX_TAG_LENGTH = 32

MAX_TEST_CASE_POINTS = 1000
