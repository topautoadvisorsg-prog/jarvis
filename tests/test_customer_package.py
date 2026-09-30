import importlib.util
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build-customer-package.py"
SPEC = importlib.util.spec_from_file_location("build_customer_package", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def example_data():
    return yaml.safe_load((ROOT / "customer-onboarding" / "example-handyman.yaml").read_text(encoding="utf-8"))


def write_spec(tmp_path, data):
    path = tmp_path / "customer.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_example_builds_installable_secret_free_distribution(tmp_path):
    spec = module.load_spec(ROOT / "customer-onboarding" / "example-handyman.yaml")
    output = module.write_package(spec, tmp_path / "package")

    expected = {
        ".gitignore", "CUSTOMER.json", "INSTALL-CHECKLIST.md", "README.md",
        "SOUL.md", "config.yaml", "distribution.yaml", "profile.yaml",
        "PACKAGE-MANIFEST.json",
    }
    assert {path.name for path in output.iterdir()} == expected
    distribution = yaml.safe_load((output / "distribution.yaml").read_text(encoding="utf-8"))
    assert distribution["name"] == "northstar-handyman"
    assert "model" not in yaml.safe_load((output / "config.yaml").read_text(encoding="utf-8"))
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in output.iterdir())
    assert "Buddy" not in all_text
    assert "JARVIS_SMARTKLIX_READ_TOKEN=" not in all_text


def test_build_is_deterministic(tmp_path):
    spec = module.load_spec(ROOT / "customer-onboarding" / "example-handyman.yaml")
    first = module.write_package(spec, tmp_path / "one")
    second = module.write_package(spec, tmp_path / "two")
    assert (first / "PACKAGE-MANIFEST.json").read_bytes() == (second / "PACKAGE-MANIFEST.json").read_bytes()


def test_base_approval_boundaries_cannot_be_removed(tmp_path):
    data = example_data()
    data["authority"]["always_require_approval"] = []
    spec = module.load_spec(write_spec(tmp_path, data))
    soul = module.render_soul(spec)
    assert "send or publish any external message" in soul
    assert "spend money" in soul
    assert "approve outreach" in soul
    assert "bypass the CRM" in soul


@pytest.mark.parametrize("field", ["api_key", "access_token", "password"])
def test_secret_fields_are_rejected(tmp_path, field):
    data = example_data()
    data["customer"][field] = "do-not-package-this"
    with pytest.raises(module.PackageError, match="secret field"):
        module.load_spec(write_spec(tmp_path, data))


def test_secret_values_are_rejected(tmp_path):
    data = example_data()
    data["business"]["summary"] = "Use Bearer abcdefghijklmnopqrstuvwxyz"
    with pytest.raises(module.PackageError, match="appears to contain a secret"):
        module.load_spec(write_spec(tmp_path, data))


def test_unknown_fields_are_rejected(tmp_path):
    data = example_data()
    data["business"]["surprise"] = "not in schema"
    with pytest.raises(module.PackageError, match="unsupported fields"):
        module.load_spec(write_spec(tmp_path, data))


def test_smartklix_selection_adds_requirements_and_boundary(tmp_path):
    data = example_data()
    data["operations"]["crm"] = "smartklix"
    data["operations"]["outreach_agents"] = "smartklix"
    spec = module.load_spec(write_spec(tmp_path, data))
    files = module.build_files(spec)
    distribution = yaml.safe_load(files["distribution.yaml"])
    assert {item["name"] for item in distribution["env_requires"]} == {
        "SMARTKLIX_CRM_BASE_URL", "SMARTKLIX_JARVIS_READ_TOKEN"
    }
    assert "existing Reviewer" in files["SOUL.md"]
    assert "sending and execution disabled" in files["INSTALL-CHECKLIST.md"]


def test_package_manifest_hashes_generated_files(tmp_path):
    spec = module.load_spec(ROOT / "customer-onboarding" / "example-handyman.yaml")
    output = module.write_package(spec, tmp_path / "package")
    manifest = json.loads((output / "PACKAGE-MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["customer_id"] == "northstar-handyman"
    assert set(manifest["files"]) == {
        ".gitignore", "CUSTOMER.json", "INSTALL-CHECKLIST.md", "README.md",
        "SOUL.md", "config.yaml", "distribution.yaml", "profile.yaml",
    }
