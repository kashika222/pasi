from pasi import __version__
from pasi.config import get_settings, load_yaml_config
from pasi.logging import configure_logging, get_logger


def test_version():
    assert __version__ == "0.1.0"


def test_settings_and_logging():
    settings = get_settings()
    assert settings.configs_dir.name == "configs"
    configure_logging()
    logger = get_logger("test")
    logger.info("scaffold ok")


def test_load_companies_yaml():
    data = load_yaml_config("configs/companies.yaml")
    assert "companies" in data
    assert len(data["companies"]) == 10
