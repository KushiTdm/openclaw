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
  status TEXT DEFAULT 'new' CHECK(status IN ('new','to_contact','contacted','interested','not_interested','closed')),
  notes TEXT,
  contacted_at DATETIME,
  last_response_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON prospects(created_at);
CREATE INDEX IF NOT EXISTS idx_city ON prospects(city);
CREATE INDEX IF NOT EXISTS idx_country ON prospects(country);

-- Table pour tracking des erreurs
CREATE TABLE IF NOT EXISTS errors_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  error_type TEXT,
  error_message TEXT,
  context TEXT,
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
