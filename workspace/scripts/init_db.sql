-- init_db.sql - Initialisation base de données prospecting
-- Path: ~/.openclaw/workspace/scripts/init_db.sql

CREATE TABLE IF NOT EXISTS prospects (
  phone_number TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  business_name TEXT,
  city TEXT,
  country TEXT,
  type TEXT CHECK(type IN ('hotel','hostel','lodge','tour_operator')),
  source TEXT DEFAULT 'google_places',
  google_maps_url TEXT,
  address TEXT,
  rating REAL,
  review_count INTEGER,
  status TEXT DEFAULT 'new' CHECK(status IN ('new','to_contact','contacted','responded_positive','responded_neutral','responded_negative','no_response','interested','not_interested','transferred_sandra','closed_won','closed_lost')),
  notes TEXT,
  contacted_at DATETIME,
  last_response_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
  -- Nouvelles colonnes pour tracking méthodes
  method_used TEXT CHECK(method_used IN ('value_education','co_investment','fake_client','pack_express','boutique_pro','enterprise')),
  response_sentiment TEXT CHECK(response_sentiment IN ('positive','neutral','negative')),
  refusal_reason TEXT,
  follow_up_needed BOOLEAN DEFAULT FALSE,
  qualification_score INTEGER,
  transferred_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON prospects(created_at);
CREATE INDEX IF NOT EXISTS idx_city ON prospects(city);
CREATE INDEX IF NOT EXISTS idx_country ON prospects(country);
CREATE INDEX IF NOT EXISTS idx_method ON prospects(method_used);

-- Table pour tracking des erreurs
CREATE TABLE IF NOT EXISTS errors_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  error_type TEXT,
  error_message TEXT,
  context TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table pour log des interactions
CREATE TABLE IF NOT EXISTS interactions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    interaction_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table pour stats quotidiennes
CREATE TABLE IF NOT EXISTS daily_stats (
  date TEXT PRIMARY KEY,
  prospects_found INTEGER DEFAULT 0,
  prospects_contacted INTEGER DEFAULT 0,
  responses_received INTEGER DEFAULT 0,
  qualified_leads INTEGER DEFAULT 0,
  api_calls_google INTEGER DEFAULT 0,
  api_calls_brave INTEGER DEFAULT 0
);

-- Table pour stats des méthodes (A/B testing)
CREATE TABLE IF NOT EXISTS method_stats (
  method_name TEXT PRIMARY KEY,
  total_sent INTEGER DEFAULT 0,
  responded INTEGER DEFAULT 0,
  interested INTEGER DEFAULT 0,
  conversion_rate REAL DEFAULT 0.0,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Initialiser les 6 méthodes
INSERT OR IGNORE INTO method_stats (method_name) VALUES
  ('value_education'),
  ('co_investment'),
  ('fake_client'),
  ('pack_express'),
  ('boutique_pro'),
  ('enterprise');
