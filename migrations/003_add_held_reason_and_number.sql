-- Add reason and number columns to held table

ALTER TABLE held ADD COLUMN reason TEXT DEFAULT '';
ALTER TABLE held ADD COLUMN number TEXT DEFAULT '';
