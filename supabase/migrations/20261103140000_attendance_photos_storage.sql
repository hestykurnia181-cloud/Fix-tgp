-- Move attendance photos out of the frequently queried attendance rows.
-- The bucket is public because the app uses its own role system rather than Supabase Auth.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('attendance-photos', 'attendance-photos', true, 1048576, ARRAY['image/jpeg','image/png','image/webp'])
ON CONFLICT (id) DO UPDATE
SET public = true,
    file_size_limit = 1048576,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "TGP attendance photos upload" ON storage.objects;
CREATE POLICY "TGP attendance photos upload"
ON storage.objects FOR INSERT TO anon, authenticated
WITH CHECK (bucket_id = 'attendance-photos');

DROP POLICY IF EXISTS "TGP attendance photos update" ON storage.objects;
CREATE POLICY "TGP attendance photos update"
ON storage.objects FOR UPDATE TO anon, authenticated
USING (bucket_id = 'attendance-photos')
WITH CHECK (bucket_id = 'attendance-photos');
