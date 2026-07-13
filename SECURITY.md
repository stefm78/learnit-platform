# Security policy

## Current scope

Learn-it Platform is currently a private bootstrap repository. No production backend, payment system, identity provider, or real learner dataset is authorized in this phase.

## Reporting a vulnerability

Do not open a public issue containing exploit details, secrets, personal data, or a reproducible attack against a deployed environment. Report the finding privately to the repository owner and include:

- affected commit or release;
- affected files or module;
- impact;
- reproduction steps;
- evidence;
- proposed containment;
- whether credentials or personal data may have been exposed.

## Mandatory controls

- Use synthetic data only.
- Store no secrets in the repository.
- Grant least privilege to workflows and external tools.
- Treat GitHub Actions, release workflows, contract validators, migrations, identity, synchronization, entitlements, and tenancy rules as security-sensitive code.
- Do not merge security-sensitive changes without independent review.
- Revoke and rotate any credential committed accidentally; deleting the file is not sufficient.

## Future platform requirements

Before any multi-user pilot, the project must provide and test:

- a threat model;
- tenant-isolation rules and negative tests;
- authentication and authorization boundaries;
- audit logging;
- data export and deletion procedures;
- backup and restoration evidence;
- idempotent synchronization and webhook handling;
- signed or otherwise verifiable published artifacts.
