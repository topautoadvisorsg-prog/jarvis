# Customer deployment package

This is the smallest reusable path from a reviewed business profile to a
separate, installable Hermes customer profile. It uses Hermes's native profile
distribution mechanism. It does not add another agent framework, CRM, reviewer,
database, or workflow engine.

Buddy's primary Hermes installation also has the `customer-deployment` skill.
Buddy can describe a customer conversationally and ask Jarvis to prepare the
package. The skill collects missing facts together, runs this same builder,
reviews its output, and stops before installation or account authorization.

## Build a package

Copy `customer-deployment/example-handyman.yaml`, replace the business facts,
and run:

```powershell
.\.venv\Scripts\python.exe scripts/build-customer-package.py `
  customer-deployment/my-customer.yaml `
  build/my-customer
```

Review the generated `CUSTOMER.json`, `SOUL.md`, and
`INSTALL-CHECKLIST.md`. Then install it on the customer's Hermes machine:

```bash
hermes profile install /path/to/build/my-customer --alias
```

The generated package includes:

- the customer's business facts and operator role;
- permanent approval and prohibition boundaries;
- low-cost default reasoning without tying the profile to a model provider;
- Hermes distribution metadata and customer-specific environment requirements;
- a separate-profile installation and acceptance checklist;
- a deterministic file-hash manifest for review and handoff.

## Safety boundary

The builder rejects unknown fields, invalid customer IDs and timezones,
secret-named fields, and common credential patterns. Generated packages never
contain API keys, tokens, sessions, memories, messages, CRM records, or another
customer's data.

The base approval rules cannot be removed by customer YAML. External sending,
spending, deletion, security changes, production deployment, and outreach
approval always require the owner. Existing CRM, Reviewer, human approval, and
deterministic execution paths remain authoritative.

## What remains customer-specific

The installer still performs the steps that require the customer's accounts:

1. configure the customer's model-provider credentials with Hermes setup;
2. connect only the integrations selected in the reviewed YAML;
3. complete OAuth, WhatsApp pairing, or CRM token setup with customer-owned
   credentials;
4. run the generated acceptance checklist before granting any narrow write
   authority.

Do not clone Buddy's live Hermes home for a customer. Use a dedicated customer
machine or account and this separate profile package.
