# Security and data handling

CareTrace is a public research demo for invented or public simulated dialogue. It is not approved for patient data or clinical decisions.

The service does not write submitted transcripts, extracted orders, or review decisions to storage. Review marks remain in page memory. The server and reverse proxy may record request metadata, such as client address, path, status, and timing. Do not enable request-body logging. An operator with host access can inspect process memory. There is no authentication, durable audit trail, or tenant isolation.

The public deployment uses the source extractor, not an external model API. Optional Ollama inference is restricted to loopback and bypasses environment HTTP proxies. Transformers may download a model when first configured. Models can return incorrect content even when JSON validation succeeds. Neither source copying nor turn-ID validation establishes clinical correctness.

Requests have a 64 KiB body limit, 40,000-character transcript limit, 300-turn limit, and one extraction slot. The in-memory limiter permits 20 extraction requests per client per minute and retains at most 2,048 clients. It resets on restart and is not a distributed abuse-prevention system. The shared deployment trusts forwarded addresses only because the container has no published port and is reached through the trusted proxy network. Keep untrusted workloads off that network.

The container runs without root, Linux capabilities, or a writable root filesystem, with memory, CPU, PID, and log limits. These controls reduce exposure; they are not a healthcare compliance certification.

For a suspected vulnerability, contact the repository owner privately through the contact information on their GitHub profile. Do not include real patient information in issues or reports. Reproduce with invented dialogue.
