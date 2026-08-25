"""Ornith batch job scheduler (Fusion dispatch target).

Dispatched tasks from the Fusion debate team land here via the REST API,
get executed one-at-a-time against the production Ornith llama-server
(:8082), with the verified circuit breaker detecting confirmation-bias
loops and forcing freeze -> fresh-context-with-negative-examples -> retry,
hard-stopping to "needs human review" after 2 freeze cycles.

Architecture contract (from the Ornith Batch Harness spec):
  * CPU-only deterministic orchestration. No model runs here.
  * The scheduler never touches the iGPU generation path directly -- it is
    a pure OpenAI-compatible client of the production llama-server.
  * Sequential execution by construction: one task at a time, so no
    prefetch/generation overlap is even possible in this process.
"""
__version__ = "0.1.0"
