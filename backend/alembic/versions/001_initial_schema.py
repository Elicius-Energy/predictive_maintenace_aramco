"""Initial schema with TimescaleDB and pgvector

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), server_default='user', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 2. devices
    op.create_table(
        'devices',
        sa.Column('device_id', sa.String(64), primary_key=True),
        sa.Column('alias', sa.String(100), nullable=True),
        sa.Column('fw_ver', sa.String(32), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expected_interval_s', sa.Integer(), server_default='60', nullable=False),
        sa.Column('status', sa.String(50), server_default='Normal', nullable=False),
        sa.Column('status_detail', sa.JSON(), nullable=False),
        sa.Column('configured', sa.Boolean(), server_default='false', nullable=False)
    )

    # 3. device_profiles
    op.create_table(
        'device_profiles',
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('nominal_voltage', sa.Float(), server_default='240.0', nullable=False),
        sa.Column('ct_rated_current', sa.Float(), server_default='100.0', nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('contact_number', sa.String(100), nullable=True),
        sa.Column('motor_make', sa.String(255), nullable=True),
        sa.Column('motor_rating_kw', sa.Float(), nullable=True),
        sa.Column('frame_size', sa.String(100), nullable=True),
        sa.Column('rated_current_amps', sa.Float(), nullable=True),
        sa.Column('rated_speed_rpm', sa.Float(), nullable=True),
        sa.Column('rated_voltage', sa.Float(), nullable=True),
        sa.Column('rated_efficiency_pct', sa.Float(), nullable=True),
        sa.Column('motor_connection', sa.String(50), nullable=True),
        sa.Column('motor_duty', sa.String(50), nullable=True),
        sa.Column('insulation_class', sa.String(50), nullable=True),
        sa.Column('motor_type', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('machine_name', sa.String(255), nullable=True),
        sa.Column('machine_make', sa.String(255), nullable=True),
        sa.Column('machine_model_no', sa.String(100), nullable=True),
        sa.Column('machine_count', sa.String(100), nullable=True),
        sa.Column('machine_tpi', sa.String(100), nullable=True),
        sa.Column('raw_material', sa.String(100), nullable=True),
        sa.Column('machine_rpm_max', sa.Float(), nullable=True),
        sa.Column('machine_rpm_avg', sa.Float(), nullable=True),
        sa.Column('no_of_spindles', sa.Integer(), nullable=True),
        sa.Column('inverter_make', sa.String(255), nullable=True),
        sa.Column('inverter_model', sa.String(255), nullable=True),
        sa.Column('rep_name', sa.String(255), nullable=True),
        sa.Column('rep_designation', sa.String(255), nullable=True),
        sa.Column('rep_contact_number', sa.String(100), nullable=True),
        sa.Column('rep_email', sa.String(255), nullable=True),
        sa.Column('signatory_customer_name', sa.String(255), nullable=True),
        sa.Column('signatory_designation', sa.String(255), nullable=True),
        sa.Column('electricity_tariff', sa.Float(), nullable=True),
        sa.Column('annual_operating_hours', sa.Float(), nullable=True),
        sa.Column('motor_investment', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('installation_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('replacement_motor_rating_kw', sa.Float(), nullable=True),
        sa.Column('replacement_motor_efficiency_pct', sa.Float(), nullable=True),
        sa.Column('idle_threshold_kw', sa.Float(), nullable=True),
        sa.Column('thresholds', sa.JSON(), nullable=False),
        sa.Column('email_alerts_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('alert_email', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 4. device_baseline
    op.create_table(
        'device_baseline',
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('per_phase_pf', sa.JSON(), nullable=False),
        sa.Column('per_phase_current_share', sa.JSON(), nullable=False),
        sa.Column('tolerance_pct', sa.Float(), server_default='30.0', nullable=False)
    )

    # 5. readings
    op.create_table(
        'readings',
        sa.Column('device_id', sa.String(64), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('fw_ver', sa.String(32), nullable=True),
        sa.Column('v1n', sa.Float(), nullable=True),
        sa.Column('v2n', sa.Float(), nullable=True),
        sa.Column('v3n', sa.Float(), nullable=True),
        sa.Column('vln_avg', sa.Float(), nullable=True),
        sa.Column('v12', sa.Float(), nullable=True),
        sa.Column('v23', sa.Float(), nullable=True),
        sa.Column('v31', sa.Float(), nullable=True),
        sa.Column('vll_avg', sa.Float(), nullable=True),
        sa.Column('i1', sa.Float(), nullable=True),
        sa.Column('i2', sa.Float(), nullable=True),
        sa.Column('i3', sa.Float(), nullable=True),
        sa.Column('i_avg', sa.Float(), nullable=True),
        sa.Column('kw1', sa.Float(), nullable=True),
        sa.Column('kw2', sa.Float(), nullable=True),
        sa.Column('kw3', sa.Float(), nullable=True),
        sa.Column('t_kw', sa.Float(), nullable=True),
        sa.Column('kvar1', sa.Float(), nullable=True),
        sa.Column('kvar2', sa.Float(), nullable=True),
        sa.Column('kvar3', sa.Float(), nullable=True),
        sa.Column('t_kvar', sa.Float(), nullable=True),
        sa.Column('kva1', sa.Float(), nullable=True),
        sa.Column('kva2', sa.Float(), nullable=True),
        sa.Column('kva3', sa.Float(), nullable=True),
        sa.Column('t_kva', sa.Float(), nullable=True),
        sa.Column('pf1', sa.Float(), nullable=True),
        sa.Column('pf2', sa.Float(), nullable=True),
        sa.Column('pf3', sa.Float(), nullable=True),
        sa.Column('pf_avg', sa.Float(), nullable=True),
        sa.Column('freq', sa.Float(), nullable=True),
        sa.Column('kwh_imp', sa.BigInteger(), nullable=True),
        sa.Column('kwh_exp', sa.BigInteger(), nullable=True),
        sa.Column('kvarh_imp', sa.BigInteger(), nullable=True),
        sa.Column('kvarh_exp', sa.BigInteger(), nullable=True),
        sa.Column('t_kvah', sa.BigInteger(), nullable=True),
        sa.Column('md_kw', sa.Float(), nullable=True),
        sa.Column('md_kvar', sa.Float(), nullable=True),
        sa.Column('md_kva', sa.Float(), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('device_id', 'ts')
    )
    op.create_index('idx_readings_device_ts', 'readings', ['device_id', 'ts'])

    # 6. alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('phase', sa.String(10), nullable=True),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cleared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False)
    )
    op.create_index('idx_alerts_open', 'alerts', ['device_id', 'type', 'phase', 'cleared_at'])

    # 7. reports
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('report_no', sa.String(100), unique=True, nullable=False),
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.String(100), server_default='admin', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('config_snapshot', sa.JSON(), nullable=False),
        sa.Column('summary', sa.JSON(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False)
    )

    # 8. kb_chunks
    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False)
    )

    if is_postgres:
        # Create hypertable
        op.execute("SELECT create_hypertable('readings', 'ts', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);")
        # Continuous aggregates
        op.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS readings_1m
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('1 minute', ts) AS bucket,
                   device_id,
                   AVG(v1n) AS v1n_avg, MIN(v1n) AS v1n_min, MAX(v1n) AS v1n_max,
                   AVG(v2n) AS v2n_avg, MIN(v2n) AS v2n_min, MAX(v2n) AS v2n_max,
                   AVG(v3n) AS v3n_avg, MIN(v3n) AS v3n_min, MAX(v3n) AS v3n_max,
                   AVG(vln_avg) AS vln_avg,
                   AVG(vll_avg) AS vll_avg,
                   AVG(i1) AS i1_avg, MIN(i1) AS i1_min, MAX(i1) AS i1_max,
                   AVG(i2) AS i2_avg, MIN(i2) AS i2_min, MAX(i2) AS i2_max,
                   AVG(i3) AS i3_avg, MIN(i3) AS i3_min, MAX(i3) AS i3_max,
                   AVG(i_avg) AS i_avg,
                   AVG(t_kw) AS kw_avg, MIN(t_kw) AS kw_min, MAX(t_kw) AS kw_max,
                   AVG(t_kva) AS kva_avg, AVG(t_kvar) AS kvar_avg,
                   AVG(pf_avg) AS pf_avg, MIN(pf_avg) AS pf_min,
                   AVG(freq) AS freq_avg,
                   AVG(t_kw) * (1.0 / 60.0) AS energy_kwh,
                   MAX(kwh_imp) AS last_kwh_imp,
                   COUNT(*) AS sample_count,
                   MAX(md_kw) AS max_md_kw
            FROM readings
            GROUP BY bucket, device_id
            WITH NO DATA;
        """)


def downgrade() -> None:
    op.drop_table('kb_chunks')
    op.drop_table('reports')
    op.drop_table('alerts')
    op.drop_table('readings')
    op.drop_table('device_baseline')
    op.drop_table('device_profiles')
    op.drop_table('devices')
    op.drop_table('users')
