-- CreateTable
CREATE TABLE "discord_users" (
    "id" TEXT NOT NULL,
    "discord_name" TEXT NOT NULL,
    "user_id" BIGINT NOT NULL,

    CONSTRAINT "discord_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ln_users" (
    "id" BIGSERIAL NOT NULL,
    "ln_key" TEXT,
    "user_id" BIGINT,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "password_users" (
    "id" BIGSERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "user_id" BIGINT NOT NULL,

    CONSTRAINT "password_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" BIGSERIAL NOT NULL,
    "pseudo" TEXT,
    "created_at" DATE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey1" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "password_users_username_key" ON "password_users"("username");

-- AddForeignKey
ALTER TABLE "discord_users" ADD CONSTRAINT "fk dc_users.users" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ln_users" ADD CONSTRAINT "ln_users_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "password_users" ADD CONSTRAINT "password_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
