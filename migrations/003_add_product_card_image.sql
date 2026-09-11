ALTER TABLE product_cards
    ADD COLUMN IF NOT EXISTS image_object_key TEXT,
    ADD COLUMN IF NOT EXISTS image_content_type TEXT,
    ADD COLUMN IF NOT EXISTS image_width INTEGER,
    ADD COLUMN IF NOT EXISTS image_height INTEGER;
