BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

-- The dump and required-file list must describe the same database snapshot.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM asset WHERE "originalPath" IS NULL OR "originalPath" = '') THEN
    RAISE EXCEPTION 'An asset has no original file path';
  END IF;
  IF EXISTS (SELECT 1 FROM asset WHERE "isExternal") THEN
    RAISE EXCEPTION 'External libraries need explicit backup mounts before this operation can run';
  END IF;
  IF EXISTS (
    SELECT 1 FROM (
      SELECT "originalPath" AS path FROM asset
      UNION ALL SELECT "sidecarPath" FROM asset
      UNION ALL SELECT "profileImagePath" FROM public."user"
    ) AS files
    WHERE path IS NOT NULL AND path <> '' AND (
      path !~ '^(/usr/src/app/)?upload/(upload|library|profile)/'
      OR path ~ '(^|/)\.\.?(/|$)'
    )
  ) THEN
    RAISE EXCEPTION 'A required media path is outside the declared backup roots';
  END IF;
END $$;

\copy (SELECT pg_export_snapshot()) TO '/backup/database/snapshot'
\o /backup/database/required-files.raw
SELECT DISTINCT CASE WHEN path LIKE '/%' THEN path ELSE '/usr/src/app/' || path END
FROM (
  SELECT "originalPath" AS path FROM asset
  UNION ALL SELECT "sidecarPath" FROM asset
  UNION ALL SELECT "profileImagePath" FROM public."user"
) AS files
WHERE path IS NOT NULL AND path <> '';
\o

\! pg_dump --snapshot="$(cat /backup/database/snapshot)" --format=custom --no-owner --no-acl --file=/backup/database/immich.dump
\if :SHELL_ERROR
  -- psql does not stop on a failed shell command unless it is checked explicitly.
  DO $$ BEGIN RAISE EXCEPTION 'pg_dump failed; no restore candidate may be created'; END $$;
\endif
COMMIT;
