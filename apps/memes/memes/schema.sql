PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS tester (
 user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL, excluded INTEGER NOT NULL DEFAULT 0, warmup_plan TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session (
 session_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES tester ON DELETE CASCADE,
 cookie_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalog (
 meme_id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, cluster_id INTEGER NOT NULL,
 kmeans_id INTEGER NOT NULL, image TEXT NOT NULL, catalog_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS impression (
 impression_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES tester ON DELETE CASCADE,
 session_id TEXT NOT NULL REFERENCES session ON DELETE CASCADE,
 meme_id INTEGER NOT NULL REFERENCES catalog, cluster_id INTEGER NOT NULL,
 arm TEXT NOT NULL CHECK(arm IN ('warmup','rec','random')), assignment_prob REAL NOT NULL,
 rank INTEGER, score REAL NOT NULL, algo_version TEXT NOT NULL, catalog_version TEXT NOT NULL,
 served_at TEXT NOT NULL, served_seq INTEGER NOT NULL, rendered_at TEXT,
 action TEXT CHECK(action IN ('like','dislike','skip')), acted_at TEXT, response_ms INTEGER,
 hidden_ms INTEGER, client_seq INTEGER,
 CHECK((action IS NULL AND acted_at IS NULL AND response_ms IS NULL AND hidden_ms IS NULL AND client_seq IS NULL) OR
 (action IS NOT NULL AND rendered_at IS NOT NULL AND acted_at IS NOT NULL AND response_ms >= 0 AND hidden_ms >= 0 AND client_seq >= 0)),
 UNIQUE(user_id,meme_id), UNIQUE(user_id,cluster_id), UNIQUE(user_id,served_seq)
);
CREATE TABLE IF NOT EXISTS event (
 event_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES tester ON DELETE CASCADE,
 impression_id INTEGER REFERENCES impression ON DELETE CASCADE,
 kind TEXT NOT NULL, occurred_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS event_immutable BEFORE UPDATE ON event BEGIN
 SELECT RAISE(ABORT,'Events are append-only');
END;
CREATE TRIGGER IF NOT EXISTS impression_immutable BEFORE UPDATE ON impression WHEN
 OLD.impression_id IS NOT NEW.impression_id OR OLD.user_id IS NOT NEW.user_id OR
 OLD.session_id IS NOT NEW.session_id OR OLD.meme_id IS NOT NEW.meme_id OR
 OLD.cluster_id IS NOT NEW.cluster_id OR OLD.arm IS NOT NEW.arm OR
 OLD.assignment_prob IS NOT NEW.assignment_prob OR OLD.rank IS NOT NEW.rank OR
 OLD.score IS NOT NEW.score OR OLD.algo_version IS NOT NEW.algo_version OR
 OLD.catalog_version IS NOT NEW.catalog_version OR OLD.served_at IS NOT NEW.served_at OR
 OLD.served_seq IS NOT NEW.served_seq OR
 (OLD.rendered_at IS NOT NULL AND OLD.rendered_at IS NOT NEW.rendered_at) OR
 (OLD.action IS NOT NULL AND (OLD.action IS NOT NEW.action OR OLD.acted_at IS NOT NEW.acted_at OR
 OLD.response_ms IS NOT NEW.response_ms OR OLD.hidden_ms IS NOT NEW.hidden_ms OR OLD.client_seq IS NOT NEW.client_seq))
 BEGIN SELECT RAISE(ABORT,'Impression fields are immutable once filled'); END;
