"""
Unit tests for configuration management

Tests:
- Settings initialization
- Environment variable loading
- Secrets validation in production
- Database URL configuration
- External service configuration
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.config import Settings, get_settings, get_config


class TestSettingsInitialization:
    """Test Settings class initialization and defaults"""

    def test_default_settings_creation(self):
        """Test that Settings can be created with defaults"""
        settings = Settings()
        assert settings is not None
        assert settings.API_TITLE == "Audiobook Automation System API"
        assert settings.API_VERSION == "1.0.0"

    def test_api_configuration(self):
        """Test API configuration values"""
        settings = Settings(
            DEBUG=True,
            API_DOCS=True,
            SECURITY_HEADERS=True
        )
        assert settings.DEBUG is True
        assert settings.API_DOCS is True
        assert settings.SECURITY_HEADERS is True

    def test_server_configuration(self):
        """Test server host and port configuration"""
        settings = Settings(
            APP_HOST="127.0.0.1",
            APP_PORT=9000
        )
        assert settings.APP_HOST == "127.0.0.1"
        assert settings.APP_PORT == 9000

    def test_database_configuration(self):
        """Test database URL configuration"""
        db_url = "postgresql://user:pass@localhost:5432/testdb"
        settings = Settings(DATABASE_URL=db_url)
        assert settings.DATABASE_URL == db_url
        assert settings.DATABASE_ECHO is False

    def test_cors_configuration(self):
        """Test CORS origins and hosts configuration"""
        settings = Settings(
            ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080",
            ALLOWED_HOSTS="localhost,127.0.0.1"
        )
        assert "localhost:3000" in settings.ALLOWED_ORIGINS
        assert "127.0.0.1" in settings.ALLOWED_HOSTS

    def test_scheduler_configuration(self):
        """Test scheduler configuration"""
        settings = Settings(SCHEDULER_ENABLED=True)
        assert settings.SCHEDULER_ENABLED is True
        assert settings.TASK_MAM_TIME == "0 2 * * *"  # Daily 2:00 AM

    def test_feature_flags(self):
        """Test feature flag configuration"""
        settings = Settings(
            ENABLE_METADATA_CORRECTION=True,
            ENABLE_SERIES_COMPLETION=True,
            ENABLE_TOP10_DISCOVERY=True
        )
        assert settings.ENABLE_METADATA_CORRECTION is True
        assert settings.ENABLE_SERIES_COMPLETION is True
        assert settings.ENABLE_TOP10_DISCOVERY is True

    def test_genres_configuration(self):
        """Test enabled and disabled genres"""
        settings = Settings()
        assert "Science Fiction" in settings.ENABLED_GENRES
        assert "Fantasy" in settings.ENABLED_GENRES
        assert "Romance" in settings.DISABLED_GENRES

    def test_project_paths(self):
        """Test project path configuration"""
        settings = Settings()
        assert isinstance(settings.PROJECT_ROOT, Path)
        assert settings.PROJECT_ROOT.exists()
        assert isinstance(settings.GUIDES_OUTPUT_DIR, Path)
        assert isinstance(settings.LOGS_DIR, Path)


class TestSecretsValidation:
    """Test secrets validation for production environment"""

    def test_secrets_not_required_in_development(self):
        """Test that secrets are optional in development environment"""
        # Development should allow empty secrets
        with patch.dict(os.environ, {"ENV": "development"}):
            settings = Settings(
                API_KEY="",
                SECRET_KEY="",
                PASSWORD_SALT=""
            )
            assert settings.API_KEY == ""
            assert settings.SECRET_KEY == ""
            assert settings.PASSWORD_SALT == ""

    def test_api_key_required_in_production(self):
        """Test that API_KEY is required in production"""
        with patch.dict(os.environ, {"ENV": "production"}):
            with pytest.raises(ValueError, match="API_KEY not set"):
                Settings(
                    API_KEY="",
                    SECRET_KEY="valid_key",
                    PASSWORD_SALT="valid_salt"
                )

    def test_secret_key_required_in_production(self):
        """Test that SECRET_KEY is required in production"""
        with patch.dict(os.environ, {"ENV": "production"}):
            with pytest.raises(ValueError, match="SECRET_KEY not set"):
                Settings(
                    API_KEY="valid_key",
                    SECRET_KEY="",
                    PASSWORD_SALT="valid_salt"
                )

    def test_password_salt_required_in_production(self):
        """Test that PASSWORD_SALT is required in production"""
        with patch.dict(os.environ, {"ENV": "production"}):
            with pytest.raises(ValueError, match="PASSWORD_SALT not set"):
                Settings(
                    API_KEY="valid_key",
                    SECRET_KEY="valid_key",
                    PASSWORD_SALT=""
                )

    def test_all_secrets_provided_in_production(self):
        """Test successful validation when all secrets are provided"""
        with patch.dict(os.environ, {"ENV": "production"}):
            settings = Settings(
                API_KEY="valid_api_key_12345",
                SECRET_KEY="valid_secret_key_12345",
                PASSWORD_SALT="valid_salt_12345"
            )
            assert settings.API_KEY == "valid_api_key_12345"
            assert settings.SECRET_KEY == "valid_secret_key_12345"
            assert settings.PASSWORD_SALT == "valid_salt_12345"

    def test_invalid_env_var_case_insensitive(self):
        """Test that ENV variable is case-insensitive"""
        # "PRODUCTION" should be treated as "production"
        with patch.dict(os.environ, {"ENV": "PRODUCTION"}):
            with pytest.raises(ValueError, match="API_KEY not set"):
                Settings(
                    API_KEY="",
                    SECRET_KEY="valid",
                    PASSWORD_SALT="valid"
                )


class TestExternalServiceConfiguration:
    """Test external service integration settings"""

    def test_audiobookshelf_configuration(self):
        """Test Audiobookshelf settings"""
        settings = Settings(
            ABS_URL="http://abs.example.com",
            ABS_TOKEN="test_token_12345",
            ABS_TIMEOUT=45
        )
        assert settings.ABS_URL == "http://abs.example.com"
        assert settings.ABS_TOKEN == "test_token_12345"
        assert settings.ABS_TIMEOUT == 45

    def test_qbittorrent_configuration(self):
        """Test qBittorrent settings"""
        settings = Settings(
            QB_HOST="http://192.168.1.100",
            QB_PORT=8080,
            QB_USERNAME="admin",
            QB_PASSWORD="password123",
            QB_TIMEOUT=60
        )
        assert settings.QB_HOST == "http://192.168.1.100"
        assert settings.QB_PORT == 8080
        assert settings.QB_USERNAME == "admin"
        assert settings.QB_PASSWORD == "password123"
        assert settings.QB_TIMEOUT == 60

    def test_prowlarr_configuration(self):
        """Test Prowlarr settings"""
        settings = Settings(
            PROWLARR_URL="http://prowlarr.example.com:9696",
            PROWLARR_API_KEY="prowlarr_key_12345",
            PROWLARR_TIMEOUT=30
        )
        assert settings.PROWLARR_URL == "http://prowlarr.example.com:9696"
        assert settings.PROWLARR_API_KEY == "prowlarr_key_12345"
        assert settings.PROWLARR_TIMEOUT == 30

    def test_google_books_configuration(self):
        """Test Google Books API settings"""
        settings = Settings(
            GOOGLE_BOOKS_API_KEY="google_books_key_12345",
            GOOGLE_BOOKS_TIMEOUT=15,
            GOOGLE_BOOKS_RATE_LIMIT=200
        )
        assert settings.GOOGLE_BOOKS_API_KEY == "google_books_key_12345"
        assert settings.GOOGLE_BOOKS_TIMEOUT == 15
        assert settings.GOOGLE_BOOKS_RATE_LIMIT == 200

    def test_mam_configuration(self):
        """Test MAM crawler settings"""
        settings = Settings(
            MAM_USERNAME="crawler_user",
            MAM_PASSWORD="crawler_pass",
            MAM_RATE_LIMIT_MIN=5,
            MAM_RATE_LIMIT_MAX=15,
            MAM_MAX_PAGES_PER_SESSION=100
        )
        assert settings.MAM_USERNAME == "crawler_user"
        assert settings.MAM_PASSWORD == "crawler_pass"
        assert settings.MAM_RATE_LIMIT_MIN == 5
        assert settings.MAM_RATE_LIMIT_MAX == 15
        assert settings.MAM_MAX_PAGES_PER_SESSION == 100


class TestSettingsCaching:
    """Test settings caching with get_settings()"""

    @patch("backend.config.Settings")
    def test_get_settings_returns_cached_instance(self, mock_settings_class):
        """Test that get_settings() returns cached instance"""
        # Clear the cache first
        get_settings.cache_clear()

        # Call get_settings twice
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance (cached)
        assert settings1 is settings2

    @patch("backend.config.Settings")
    def test_get_config_returns_settings(self, mock_settings_class):
        """Test that get_config() returns Settings"""
        get_settings.cache_clear()
        result = get_config()
        assert result is not None


class TestEnvironmentVariableLoading:
    """Test environment variable loading"""

    def test_settings_loads_from_env(self):
        """Test that Settings loads values from environment variables"""
        with patch.dict(os.environ, {
            "APP_HOST": "0.0.0.0",
            "APP_PORT": "9000",
            "DEBUG": "true"
        }):
            # Create new settings to reload from env
            settings = Settings()
            assert settings.APP_HOST == "0.0.0.0"
            assert settings.APP_PORT == 9000
            assert settings.DEBUG is True

    def test_settings_model_config(self):
        """Test Settings model configuration"""
        assert Settings.model_config["env_file"] == ".env"
        assert Settings.model_config["case_sensitive"] is True
        assert Settings.model_config["extra"] == "ignore"


class TestDataRetentionPolicy:
    """Test data retention configuration"""

    def test_history_retention_days(self):
        """Test history retention days setting"""
        settings = Settings(HISTORY_RETENTION_DAYS=60)
        assert settings.HISTORY_RETENTION_DAYS == 60

    def test_failed_attempts_retention(self):
        """Test failed attempts retention policy"""
        settings = Settings(FAILED_ATTEMPTS_RETENTION="permanent")
        assert settings.FAILED_ATTEMPTS_RETENTION == "permanent"


class TestGapAnalysisConfiguration:
    """Test gap analysis feature configuration"""

    def test_gap_analysis_enabled(self):
        """Test gap analysis feature toggle"""
        settings = Settings(GAP_ANALYSIS_ENABLED=True)
        assert settings.GAP_ANALYSIS_ENABLED is True

    def test_gap_analysis_parameters(self):
        """Test gap analysis parameters"""
        settings = Settings(
            GAP_MAX_DOWNLOADS_PER_RUN=20,
            GAP_SERIES_PRIORITY=True,
            GAP_AUTHOR_PRIORITY=True,
            MAM_MIN_SEEDS=3,
            MAM_TITLE_MATCH_THRESHOLD=0.85
        )
        assert settings.GAP_MAX_DOWNLOADS_PER_RUN == 20
        assert settings.GAP_SERIES_PRIORITY is True
        assert settings.GAP_AUTHOR_PRIORITY is True
        assert settings.MAM_MIN_SEEDS == 3
        assert settings.MAM_TITLE_MATCH_THRESHOLD == 0.85
