"""Run additive control-plane migrations.

Usage: python -m scripts.migrate_control
"""

from app.migrations.security_records import main


if __name__ == "__main__":
    main()
