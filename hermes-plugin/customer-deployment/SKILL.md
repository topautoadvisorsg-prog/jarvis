---
name: customer-deployment
description: Prepare a separate, secret-free Hermes customer pilot package from plain business information. Use when Buddy asks to set up, package, or prepare a new customer deployment.
version: 0.1.0
author: Smart Klix
license: Proprietary
metadata:
  hermes:
    tags: [customers, profiles, deployment]
---

# Customer deployment

## Purpose

Turn the owner's plain-language description of a new customer into a reviewed,
installable Hermes profile distribution. This prepares files only. It does not
install a profile, connect an account, copy credentials, or grant authority.

## Source of truth

Use the checked-in schema and builder from the Jarvis source repository:

- `customer-deployment/example-handyman.yaml`
- `scripts/build-customer-package.py`
- `docs/CUSTOMER-DEPLOYMENT-PACKAGE.md`

For Buddy's current machine, the authoritative checkout is:

`/mnt/c/Users/jovan/Documents/Codex/2026-09-07/files-pasted-by-the-user-you/work/hermes-jarvis-reference`

If that checkout is unavailable, find a repository containing all three files.
Do not recreate the schema from memory or silently use the live HUD checkout.

## Procedure

1. Extract any supplied facts into the existing schema. Never invent the
   business name, owner, services, service territory, hours, or connected
   systems.
2. If required facts are missing, ask for all missing facts together in one
   concise request. Explain choices in ordinary language:
   - `crm`: `smartklix` only when this customer will use SmartKlix CRM;
   - `outreach_agents`: `smartklix` only when existing Smart Klix Claude Agents
     are part of this deployment;
   - `whatsapp`: true only when the customer wants that transport;
   - `personal_google_readonly`: true only for customer-owned read-only Gmail
     and Calendar access.
3. Keep API keys, passwords, tokens, OAuth files, phone numbers, customer
   messages, lead records, and existing runtime data out of the intake file.
   Tell the owner to enter credentials during the later account setup step.
4. Write the reviewed intake YAML under
   `~/.hermes/customer-intake/<customer-id>.yaml`. Create the directory if
   needed and keep it private to the current OS user.
5. Run the builder with Hermes's Python environment:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python \
     <jarvis-source>/scripts/build-customer-package.py \
     ~/.hermes/customer-intake/<customer-id>.yaml \
     ~/.hermes/customer-packages/<customer-id>-<timestamp>
   ```

   Use a new timestamped output directory. Do not overwrite an earlier package.
6. Read the generated `CUSTOMER.json`, `SOUL.md`, `distribution.yaml`, and
   `INSTALL-CHECKLIST.md`. Confirm the identity and operating boundaries match
   the supplied facts. Confirm the package has no `.env`, auth, session,
   memory, database, message, or credential file.
7. Report the output directory, selected integrations, approval boundaries,
   and exact customer-owned setup still pending. Show the checklist on the HUD
   when the owner asks to see it.
8. Stop. Installation, OAuth, WhatsApp pairing, CRM tokens, write authority,
   spending, sending, and production deployment remain separate approved work.

## Permanent boundaries

- Use the existing Hermes profile distribution mechanism.
- Do not create another manager agent, CRM, reviewer, database, or workflow
  engine.
- Do not clone Buddy's Hermes home or any other customer's runtime state.
- Do not weaken the builder's base approval or prohibition rules.
- Do not install or enable tools merely because the customer selected them in
  the intake. Selection means they appear in the later installation checklist.
- Existing SmartKlix CRM, Reviewer, human approval, and deterministic executor
  remain authoritative whenever SmartKlix is selected.

## Completion check

The output is a newly generated Hermes distribution, the customer facts are
accurate, no secret or runtime data is present, consequential actions still
require approval, and the installer has a clear list of pending account steps.
