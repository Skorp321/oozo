-- Миграция: add_hr_usage_metrics.sql
-- Таблица агрегированных продуктовых метрик DAU/MAU/Retention

CREATE TABLE IF NOT EXISTS "oozo-schema".hr_usage_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL UNIQUE,
    dau INTEGER,
    mau INTEGER,
    retention_week NUMERIC(5,2),
    retention_month NUMERIC(5,2),
    retention_quarter NUMERIC(5,2),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL,
    source_timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow'
);

COMMENT ON TABLE "oozo-schema".hr_usage_metrics IS 'Снимки продуктовых метрик DAU/MAU/Retention';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.metric_date IS 'Дата среза метрик (MSK)';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.dau IS 'Daily Active Users за дату metric_date';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.mau IS 'Monthly Active Users, рассчитанный в 1-й день месяца в 03:00 MSK';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.retention_week IS 'Retention %: доля пользователей с >1 днями активности за последние 7 дней';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.retention_month IS 'Retention %: доля пользователей с >1 днями активности за последние 30 дней';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.retention_quarter IS 'Retention %: доля пользователей с >1 днями активности за последние 90 дней';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.calculated_at IS 'UTC время расчета и записи метрик';
COMMENT ON COLUMN "oozo-schema".hr_usage_metrics.source_timezone IS 'Таймзона, в которой делался расчет';

CREATE INDEX IF NOT EXISTS idx_hr_usage_metrics_metric_date ON "oozo-schema".hr_usage_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_hr_usage_metrics_calculated_at ON "oozo-schema".hr_usage_metrics(calculated_at);
