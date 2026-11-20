-- Analytics summary views
-- Run: psql -U traveldoc -d traveldoc -f /app/db/sql/analytics_views.sql

CREATE OR REPLACE VIEW v_event_counts AS
SELECT
    event_name,
    COUNT(*) AS total_events,
    COUNT(DISTINCT session_id) AS unique_sessions,
    DATE_TRUNC('day', created_at) AS event_date
FROM analytics_events
GROUP BY event_name, DATE_TRUNC('day', created_at)
ORDER BY event_date DESC, total_events DESC;

CREATE OR REPLACE VIEW v_top_languages AS
SELECT
    language_code,
    COUNT(*) AS search_count,
    DATE_TRUNC('day', created_at) AS search_date
FROM search_requests
GROUP BY language_code, DATE_TRUNC('day', created_at)
ORDER BY search_date DESC, search_count DESC;

CREATE OR REPLACE VIEW v_top_needs AS
SELECT
    need_category,
    COUNT(*) AS search_count,
    AVG(results_count) AS avg_results
FROM search_requests
GROUP BY need_category
ORDER BY search_count DESC;

CREATE OR REPLACE VIEW v_provider_engagement AS
SELECT
    (properties->>'provider_id')::text AS provider_id,
    SUM(CASE WHEN event_name = 'provider_opened' THEN 1 ELSE 0 END) AS profile_views,
    SUM(CASE WHEN event_name = 'call_tapped' THEN 1 ELSE 0 END) AS call_taps,
    SUM(CASE WHEN event_name = 'whatsapp_tapped' THEN 1 ELSE 0 END) AS whatsapp_taps,
    SUM(CASE WHEN event_name = 'directions_tapped' THEN 1 ELSE 0 END) AS direction_taps
FROM analytics_events
WHERE event_name IN ('provider_opened', 'call_tapped', 'whatsapp_tapped', 'directions_tapped')
  AND properties->>'provider_id' IS NOT NULL
GROUP BY properties->>'provider_id'
ORDER BY profile_views DESC;
