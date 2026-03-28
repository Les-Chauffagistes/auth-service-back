/*
  Warnings:

  - Changed the type of `status` on the `lnurl_auth` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.

*/
-- CreateEnum
CREATE TYPE "lnurl_auth_status" AS ENUM ('pending', 'done');

-- AlterTable
ALTER TABLE "lnurl_auth" DROP COLUMN "status",
ADD COLUMN     "status" "lnurl_auth_status" NOT NULL;
