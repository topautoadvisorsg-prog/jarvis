from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "hermes-plugin" / "customer-deployment" / "SKILL.md"


def skill_parts():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_skill_has_valid_identity_and_trigger():
    meta, body = skill_parts()
    assert meta["name"] == "customer-deployment"
    assert "new customer" in meta["description"].lower()
    assert "build-customer-package.py" in body


def test_skill_preserves_customer_and_authority_boundaries():
    _, body = skill_parts()
    body = body.lower()
    required = [
        "this prepares files only",
        "keep api keys",
        "do not clone buddy's hermes home",
        "do not weaken the builder's base approval",
        "existing smartklix crm, reviewer, human approval, and deterministic executor",
        "stop. installation, oauth, whatsapp pairing, crm tokens, write authority",
    ]
    for phrase in required:
        assert phrase in body


def test_skill_uses_private_intake_and_timestamped_output():
    _, body = skill_parts()
    assert "~/.hermes/customer-intake/<customer-id>.yaml" in body
    assert "~/.hermes/customer-packages/<customer-id>-<timestamp>" in body
    assert "Do not overwrite an earlier package" in body
