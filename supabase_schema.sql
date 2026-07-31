-- Mengaktifkan ekstensi UUID (dibutuhkan untuk uuid_generate_v4)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- Tabel: user_configs
-- ==========================================
-- Buat tabel user_configs
CREATE TABLE IF NOT EXISTS public.user_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_user_id UNIQUE(user_id)
);

-- Mengaktifkan Row Level Security (RLS)
ALTER TABLE public.user_configs ENABLE ROW LEVEL SECURITY;

-- Kebijakan RLS: Pengguna hanya bisa membaca konfigurasi miliknya sendiri
CREATE POLICY "Users can view own config" 
ON public.user_configs FOR SELECT 
USING (auth.uid() = user_id);

-- Kebijakan RLS: Pengguna hanya bisa menambah/memperbarui konfigurasi miliknya sendiri
CREATE POLICY "Users can insert own config" 
ON public.user_configs FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own config" 
ON public.user_configs FOR UPDATE 
USING (auth.uid() = user_id) 
WITH CHECK (auth.uid() = user_id);


-- ==========================================
-- Kebijakan untuk Storage Bucket 'user_files'
-- ==========================================
-- Membuat bucket 'user_files' jika belum ada (Membutuhkan akses admin/SQL Editor)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('user_files', 'user_files', false) 
ON CONFLICT (id) DO NOTHING;

-- Kebijakan: Pengguna hanya bisa membaca file di dalam folder (path) user_id mereka sendiri
DROP POLICY IF EXISTS "Users can view own files" ON storage.objects;
CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'user_files' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Kebijakan: Pengguna hanya bisa mengunggah file ke dalam folder user_id mereka sendiri
DROP POLICY IF EXISTS "Users can upload own files" ON storage.objects;
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'user_files' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Kebijakan: Pengguna hanya bisa memperbarui (overwrite) file mereka sendiri
DROP POLICY IF EXISTS "Users can update own files" ON storage.objects;
CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'user_files' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Kebijakan: Pengguna hanya bisa menghapus file mereka sendiri
DROP POLICY IF EXISTS "Users can delete own files" ON storage.objects;
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'user_files' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);
