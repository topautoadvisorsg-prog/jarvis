from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "cua-read-only.yaml"
WRAPPER = ROOT / "scripts" / "cua-driver-wsl-wrapper.sh"


EXPECTED_READ_TOOLS = {
    "start_session",
    "end_session",
    "list_apps",
    "list_windows",
    "get_screen_size",
    "get_desktop_state",
    "health_report",
    "check_permissions",
}

ACTION_TOOLS = {
    "bring_to_front",
    "browser_click",
    "browser_download",
    "browser_navigate",
    "browser_pointer",
    "browser_prepare",
    "browser_set_input_files",
    "browser_type",
    "click",
    "clipboard_read",
    "clipboard_write",
    "double_click",
    "drag",
    "hotkey",
    "invoke_menu",
    "kill_app",
    "launch_app",
    "move_cursor",
    "page",
    "press_key",
    "replay_trajectory",
    "right_click",
    "scroll",
    "set_config",
    "set_value",
    "set_window_frame",
    "start_recording",
    "type_text",
    "zoom",
}


def test_capability_manifest_is_v3_expiring_and_read_only():
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == 3
    assert manifest["expires_after"]
    assert manifest["idle_timeout"]
    assert set(manifest["allow"]["tools"]) == EXPECTED_READ_TOOLS
    assert ACTION_TOOLS.isdisjoint(manifest["allow"]["tools"])
    assert manifest["resources"] == {"desktop": {"display": True}}


def test_wsl_wrapper_translates_only_host_boundary_arguments():
    source = WRAPPER.read_text(encoding="utf-8")

    assert "--socket" in source
    assert "--capability-manifest" in source
    assert "wslpath -w" in source
    assert "%LOCALAPPDATA%" in source
    assert "</dev/null" in source
    assert "/Users/jovan/" not in source
    assert 'manifest["mcp_invocation"]["command"]' in source
    assert 'exec "$driver" "${args[@]}"' in source
