# Integration audit

Verified in source:

- eight locked biomarkers and fixed preprocessing order;
- server-side public sample resolution;
- 15-sample training-only catalog shape;
- catalog SHA-256 validation before inference;
- upload suffix and size validation;
- explicit CORS origins and request IDs.

The full quantum integration test remains environment-blocked until the pinned
`qiskit-machine-learning` dependency is installed. No held-out test evaluator or test
array was accessed.