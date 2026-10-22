"""
Database initialization and seeding script.
Sets up TimescaleDB hypertables, continuous aggregates, admin account, devices, and KB embeddings.
"""
import os
import glob
import logging
from pathlib import Path
from sqlalchemy import text
from app.config import settings
from app.db.base import Base, engine, SessionLocal
from app.db.models import User, Device, DeviceProfile, KBChunk
from app.core.security import hash_password, verify_password

logger = logging.getLogger(__name__)


def init_db():
    """Initialize database tables, extensions, aggregates, and seed data."""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    _ensure_user_columns()
    _ensure_report_profile_columns()
    
    # Check if database is PostgreSQL
    is_postgres = engine.dialect.name == "postgresql"
    if is_postgres:
        _setup_timescaledb()
        
    db = SessionLocal()
    try:
        _seed_admin_user(db)
        _seed_devices(db)
        _seed_kb_chunks(db)
        _auto_migrate_legacy_db(db)
        db.commit()
        logger.info("Database initialized and seeded successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Error during database seeding: %s", str(e), exc_info=True)
    finally:
        db.close()


def _ensure_report_profile_columns():
    """Add report profile fields to existing SQLite or PostgreSQL databases."""
    with engine.begin() as conn:
        additions = {
            "rated_efficiency_pct": "FLOAT",
            "replacement_motor_rating_kw": "FLOAT",
            "replacement_motor_efficiency_pct": "FLOAT",
        }
        if engine.dialect.name == "sqlite":
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(device_profiles)"))}
            for name, sql_type in additions.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE device_profiles ADD COLUMN {name} {sql_type}"))
        elif engine.dialect.name == "postgresql":
            for name, sql_type in additions.items():
                conn.execute(text(f"ALTER TABLE device_profiles ADD COLUMN IF NOT EXISTS {name} {sql_type}"))


def _ensure_user_columns():
    """Add account lifecycle fields to databases created by previous app versions."""
    additions = {
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
        "must_change_password": "BOOLEAN NOT NULL DEFAULT FALSE",
        "session_version": "INTEGER NOT NULL DEFAULT 0",
        "mfa_secret": "VARCHAR(64)",
        "mfa_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
            for name, sql_type in additions.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))
        else:
            for name, sql_type in additions.items():
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {sql_type}"))
        conn.execute(text("UPDATE users SET role = 'viewer' WHERE lower(role) IN ('user', 'operator')"))


def _setup_timescaledb():
    """Apply TimescaleDB hypertables, compression, retention, and continuous aggregates."""
    logger.info("Configuring TimescaleDB and pgvector extensions...")
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Convert readings to hypertable
            conn.execute(text("""
                SELECT create_hypertable('readings', 'ts', 
                    chunk_time_interval => INTERVAL '1 day', 
                    if_not_exists => TRUE
                );
            """))
            
            # Enable compression after 7 days
            try:
                conn.execute(text("""
                    ALTER TABLE readings SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'device_id',
                        timescaledb.compress_orderby = 'ts DESC'
                    );
                """))
                conn.execute(text("SELECT add_compression_policy('readings', INTERVAL '7 days', if_not_exists => TRUE);"))
            except Exception as comp_err:
                logger.info("Compression policy notice: %s", str(comp_err))
                
            # Retention policy 24 months
            try:
                conn.execute(text("SELECT add_retention_policy('readings', INTERVAL '24 months', if_not_exists => TRUE);"))
            except Exception as ret_err:
                logger.info("Retention policy notice: %s", str(ret_err))
                
            # Create Continuous Aggregates: readings_1m
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS readings_1m
                WITH (timescaledb.continuous) AS
                SELECT time_bucket('1 minute', ts) AS bucket,
                       device_id,
                       AVG(v1n) AS v1n_avg, MIN(v1n) AS v1n_min, MAX(v1n) AS v1n_max,
                       AVG(v2n) AS v2n_avg, MIN(v2n) AS v2n_min, MAX(v2n) AS v2n_max,
                       AVG(v3n) AS v3n_avg, MIN(v3n) AS v3n_min, MAX(v3n) AS v3n_max,
                       AVG(vln_avg) AS vln_avg, MIN(vln_avg) AS vln_min, MAX(vln_avg) AS vln_max,
                       AVG(vll_avg) AS vll_avg,
                       AVG(i1) AS i1_avg, MIN(i1) AS i1_min, MAX(i1) AS i1_max,
                       AVG(i2) AS i2_avg, MIN(i2) AS i2_min, MAX(i2) AS i2_max,
                       AVG(i3) AS i3_avg, MIN(i3) AS i3_min, MAX(i3) AS i3_max,
                       AVG(i_avg) AS i_avg, MIN(i_avg) AS i_min, MAX(i_avg) AS i_max,
                       AVG(t_kw) AS kw_avg, MIN(t_kw) AS kw_min, MAX(t_kw) AS kw_max,
                       AVG(t_kva) AS kva_avg, AVG(t_kvar) AS kvar_avg,
                       AVG(pf_avg) AS pf_avg, MIN(pf_avg) AS pf_min,
                       AVG(freq) AS freq_avg, MIN(freq) AS freq_min, MAX(freq) AS freq_max,
                       AVG(t_kw) * (1.0 / 60.0) AS energy_kwh,
                       MAX(kwh_imp) AS last_kwh_imp,
                       COUNT(*) AS sample_count,
                       MAX(md_kw) AS max_md_kw
                FROM readings
                GROUP BY bucket, device_id
                WITH NO DATA;
            """))
            
            # Continuous Aggregate: readings_5m
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS readings_5m
                WITH (timescaledb.continuous) AS
                SELECT time_bucket('5 minutes', ts) AS bucket,
                       device_id,
                       AVG(v1n) AS v1n_avg, MIN(v1n) AS v1n_min, MAX(v1n) AS v1n_max,
                       AVG(v2n) AS v2n_avg, MIN(v2n) AS v2n_min, MAX(v2n) AS v2n_max,
                       AVG(v3n) AS v3n_avg, MIN(v3n) AS v3n_min, MAX(v3n) AS v3n_max,
                       AVG(vln_avg) AS vln_avg, MIN(vln_avg) AS vln_min, MAX(vln_avg) AS vln_max,
                       AVG(vll_avg) AS vll_avg,
                       AVG(i1) AS i1_avg, MIN(i1) AS i1_min, MAX(i1) AS i1_max,
                       AVG(i2) AS i2_avg, MIN(i2) AS i2_min, MAX(i2) AS i2_max,
                       AVG(i3) AS i3_avg, MIN(i3) AS i3_min, MAX(i3) AS i3_max,
                       AVG(i_avg) AS i_avg, MIN(i_avg) AS i_min, MAX(i_avg) AS i_max,
                       AVG(t_kw) AS kw_avg, MIN(t_kw) AS kw_min, MAX(t_kw) AS kw_max,
                       AVG(t_kva) AS kva_avg, AVG(t_kvar) AS kvar_avg,
                       AVG(pf_avg) AS pf_avg, MIN(pf_avg) AS pf_min,
                       AVG(freq) AS freq_avg, MIN(freq) AS freq_min, MAX(freq) AS freq_max,
                       AVG(t_kw) * (5.0 / 60.0) AS energy_kwh,
                       MAX(kwh_imp) AS last_kwh_imp,
                       COUNT(*) AS sample_count,
                       MAX(md_kw) AS max_md_kw
                FROM readings
                GROUP BY bucket, device_id
                WITH NO DATA;
            """))

            # Continuous Aggregate: readings_1h
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS readings_1h
                WITH (timescaledb.continuous) AS
                SELECT time_bucket('1 hour', ts) AS bucket,
                       device_id,
                       AVG(v1n) AS v1n_avg, MIN(v1n) AS v1n_min, MAX(v1n) AS v1n_max,
                       AVG(v2n) AS v2n_avg, MIN(v2n) AS v2n_min, MAX(v2n) AS v2n_max,
                       AVG(v3n) AS v3n_avg, MIN(v3n) AS v3n_min, MAX(v3n) AS v3n_max,
                       AVG(vln_avg) AS vln_avg, MIN(vln_avg) AS vln_min, MAX(vln_avg) AS vln_max,
                       AVG(vll_avg) AS vll_avg,
                       AVG(i1) AS i1_avg, MIN(i1) AS i1_min, MAX(i1) AS i1_max,
                       AVG(i2) AS i2_avg, MIN(i2) AS i2_min, MAX(i2) AS i2_max,
                       AVG(i3) AS i3_avg, MIN(i3) AS i3_min, MAX(i3) AS i3_max,
                       AVG(i_avg) AS i_avg, MIN(i_avg) AS i_min, MAX(i_avg) AS i_max,
                       AVG(t_kw) AS kw_avg, MIN(t_kw) AS kw_min, MAX(t_kw) AS kw_max,
                       AVG(t_kva) AS kva_avg, AVG(t_kvar) AS kvar_avg,
                       AVG(pf_avg) AS pf_avg, MIN(pf_avg) AS pf_min,
                       AVG(freq) AS freq_avg, MIN(freq) AS freq_min, MAX(freq) AS freq_max,
                       AVG(t_kw) * 1.0 AS energy_kwh,
                       MAX(kwh_imp) AS last_kwh_imp,
                       COUNT(*) AS sample_count,
                       MAX(md_kw) AS max_md_kw
                FROM readings
                GROUP BY bucket, device_id
                WITH NO DATA;
            """))
            logger.info("TimescaleDB continuous aggregates verified.")
        except Exception as ts_err:
            logger.warning("TimescaleDB initialization notice: %s", str(ts_err))


def _seed_admin_user(db):
    """Seed the default administrator account."""
    for existing_admin in db.query(User).filter(User.role.ilike("admin")).all():
        if verify_password("admin123", existing_admin.password_hash):
            existing_admin.must_change_password = True
            logger.warning("Existing default admin password detected; password change is required at next sign in.")
    admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
    if not admin:
        if not settings.ADMIN_PASSWORD_HASH and len(settings.ADMIN_PASSWORD) < 12:
            logger.error("Refusing to seed an admin password shorter than 12 characters. Configure ADMIN_PASSWORD or ADMIN_PASSWORD_HASH.")
            return
        hashed = settings.ADMIN_PASSWORD_HASH or hash_password(settings.ADMIN_PASSWORD)
        admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hashed,
            role="admin"
        )
        db.add(admin)
        logger.info("Admin user '%s' seeded successfully.", settings.ADMIN_USERNAME)


def _seed_devices(db):
    """No-op: devices must be manually registered by the user via the Configuration page."""
    logger.info("Device seeding skipped – manual registration required.")


def _seed_kb_chunks(db):
    """Seed markdown knowledge base files into kb_chunks for RAG."""
    kb_path = Path(settings.KB_DIR)
    if not kb_path.exists():
        logger.warning("KB directory %s does not exist; skipping KB seeding.", str(kb_path))
        return
        
    md_files = glob.glob(str(kb_path / "*.md"))
    for file_path in md_files:
        p = Path(file_path)
        source = p.stem
        existing = db.query(KBChunk).filter(KBChunk.source == source).first()
        if not existing:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            title = p.name.replace("_", " ").replace(".md", "").title()
            chunk = KBChunk(
                source=source,
                title=title,
                content=content,
                embedding=None,  # Generated by RAG engine when OpenAI is called or on demand
                metadata_json={"filename": p.name}
            )
            db.add(chunk)
            logger.info("Knowledge chunk '%s' loaded into database.", source)


def _auto_migrate_legacy_db(db):
    """Automatically retain and migrate legacy sensor_data.db data if present."""
    candidates = [
        Path("/app/backend_data/sensor_data.db"),
        Path("/app/data/sensor_data.db"),
        Path(__file__).resolve().parent.parent.parent / "backend" / "data" / "sensor_data.db",
        Path(__file__).resolve().parent.parent.parent.parent / "backend" / "data" / "sensor_data.db",
    ]
    src_db = None
    for c in candidates:
        if c.exists() and c.is_file():
            src_db = c
            break

    if not src_db:
        return

    logger.info("Legacy database detected at %s. Checking if historical data needs migration...", src_db)
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{src_db}?immutable=1", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_readings'")
        if not cursor.fetchone():
            conn.close()
            return

        total_legacy = cursor.execute("SELECT count(*) FROM sensor_readings").fetchone()[0]
        conn.close()

        from app.db.models import Reading
        current_readings = db.query(Reading).count()
        if current_readings < total_legacy:
            logger.info("Found %d legacy readings (current active DB has %d). Running migration to retain historical data...", total_legacy, current_readings)
            # Import and run migration
            sys_path = str(Path(__file__).resolve().parent.parent.parent / "scripts")
            if sys_path not in sys.path:
                sys.path.append(sys_path)
            try:
                import migrate_historical_data
                migrate_historical_data.run_migration()
                logger.info("Historical data migration completed successfully.")
            except Exception as mig_err:
                logger.error("Auto-migration notice: %s", str(mig_err))
        else:
            logger.info("Historical readings are already fully retained (%d records in active database).", current_readings)
    except Exception as e:
        logger.warning("Could not complete legacy database check: %s", str(e))


if __name__ == "__main__":
    init_db()

