-- schema.prisma marked `ln_users.ln_key` as `@unique` in the "added linked providers
-- flow" commit, but no migration was generated for it, so the constraint was never
-- actually applied to the database.
CREATE UNIQUE INDEX "ln_users_ln_key_key" ON "ln_users"("ln_key");
