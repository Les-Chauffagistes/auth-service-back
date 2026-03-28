-- CreateTable
CREATE TABLE "lnurl_auth" (
    "k1" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT,

    CONSTRAINT "lnurl_auth_pkey" PRIMARY KEY ("k1")
);

-- AddForeignKey
ALTER TABLE "lnurl_auth" ADD CONSTRAINT "ln_users_lnurl_auth_fk" FOREIGN KEY ("user_id") REFERENCES "ln_users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
