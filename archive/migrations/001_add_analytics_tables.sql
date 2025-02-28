-- Add analytics tables for menu items
CREATE TABLE menu_item_analytics (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    views INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue NUMERIC(10,2) DEFAULT 0,
    last_ordered TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT positive_metrics CHECK (views >= 0 AND orders >= 0 AND revenue >= 0)
);

CREATE TABLE item_popularity_history (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    date DATE,
    orders INTEGER,
    revenue NUMERIC(10,2),
    CONSTRAINT unique_daily_stats UNIQUE (item_id, date),
    CONSTRAINT positive_history_metrics CHECK (orders >= 0 AND revenue >= 0)
);

-- Add indexes for performance
CREATE INDEX idx_analytics_item_id ON menu_item_analytics(item_id);
CREATE INDEX idx_history_item_date ON item_popularity_history(item_id, date);

-- Add trigger to maintain 3-month retention period
CREATE OR REPLACE FUNCTION prune_old_history() RETURNS trigger AS $$
BEGIN
    DELETE FROM item_popularity_history 
    WHERE date < CURRENT_DATE - INTERVAL '3 months';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prune_history_trigger
    AFTER INSERT ON item_popularity_history
    EXECUTE FUNCTION prune_old_history();
