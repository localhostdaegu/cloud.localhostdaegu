"""Settings 가 루트 .env(도커 컴포즈 공용) 와 backend/.env 를 순서대로 읽는지 — 뒤가 우선."""

from pathlib import Path

from core.matrix.grid_keymaker_secret_manager import Settings

_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent


def test_settings_reads_root_env_then_backend_env():
    assert Settings.model_config["env_file"] == (_ROOT / ".env", _BACKEND / ".env")


def test_settings_ignores_empty_values_so_backend_env_placeholder_does_not_mask_root():
    # backend/.env 의 'KEY=' 빈 줄이 루트 .env 값을 빈 문자열로 덮어쓰면 안 된다
    assert Settings.model_config["env_ignore_empty"] is True


def test_settings_declares_youthcenter_key():
    assert "youthcenter_api_key" in Settings.model_fields


def test_settings_declares_gemini_report_model_with_default():
    assert Settings.model_fields["gemini_report_model"].default == "gemini-2.5-flash"
