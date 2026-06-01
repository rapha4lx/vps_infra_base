-- ============================================
-- Schema convertido do Prisma
-- Projeto: service_flow
-- ============================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$ BEGIN
    CREATE TYPE "DataSource" AS ENUM ('BLIP', 'ZENDESK', 'CSV', 'JSON');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE "AutomationType" AS ENUM ('informacional', 'transacional');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE "AutomationPossible" AS ENUM ('sim', 'nao');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE "StatusTicket" AS ENUM ('resolvido', 'nao_resolvido');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE "UserRole" AS ENUM ('SITE_ADMIN', 'COMPANY_ADMIN', 'COMPANY_MEMBER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE "InviteType" AS ENUM ('ADMIN_CREATED', 'MEMBER_CREATED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS "Company" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "User" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    "lastLoginAt" TIMESTAMP,
    role "UserRole" NOT NULL DEFAULT 'COMPANY_MEMBER',
    "companyId" UUID,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "User_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS "CompanyDataSourceApiKey" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "companyId" UUID NOT NULL,
    source "DataSource" NOT NULL,
    name VARCHAR(255) NOT NULL,
    "apiKey" VARCHAR(255) NOT NULL,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "CompanyDataSourceApiKey_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"(id) ON DELETE CASCADE,
    UNIQUE ("companyId", name)
);

CREATE TABLE IF NOT EXISTS "UserCredential" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "userId" UUID NOT NULL,
    provider VARCHAR(255),
    "providerId" VARCHAR(255),
    "passwordHash" VARCHAR(255),
    CONSTRAINT "UserCredential_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "RefreshToken" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "userId" UUID NOT NULL,
    token VARCHAR(255) NOT NULL,
    "expiresAt" TIMESTAMP NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT false,
    "ipAddress" VARCHAR(255),
    "userAgent" TEXT,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "RefreshToken_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "Ticket" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "customerIdentity" VARCHAR(255) NOT NULL,
    "ownerIdentity" VARCHAR(255),
    "agentIdentity" VARCHAR(255),
    status VARCHAR(255) NOT NULL,
    team VARCHAR(255),
    tags TEXT[] NOT NULL DEFAULT '{}',
    "openDate" TIMESTAMP NOT NULL,
    "closedDate" TIMESTAMP,
    "companyId" UUID,
    "dataSourceApiKeyId" UUID,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "Ticket_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"(id) ON DELETE SET NULL,
    CONSTRAINT "Ticket_dataSourceApiKeyId_fkey" FOREIGN KEY ("dataSourceApiKeyId") REFERENCES "CompanyDataSourceApiKey"(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS "Invite" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(255) NOT NULL UNIQUE,
    type "InviteType" NOT NULL,
    "targetRole" "UserRole" NOT NULL DEFAULT 'COMPANY_MEMBER',
    "companyId" UUID NOT NULL,
    "createdByUserId" UUID,
    "maxUses" INTEGER,
    "usedCount" INTEGER NOT NULL DEFAULT 0,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "expiresAt" TIMESTAMP,
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "Invite_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"(id) ON DELETE CASCADE,
    CONSTRAINT "Invite_createdByUserId_fkey" FOREIGN KEY ("createdByUserId") REFERENCES "User"(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS "TicketMetadata" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "ticketId" UUID NOT NULL,
    "averageTimeInCategory" FLOAT,
    summary TEXT,
    "summaryAnonymized" TEXT,
    detail TEXT,
    category VARCHAR(255),
    "subCategory" VARCHAR(255),
    "actionType" VARCHAR(255),
    "automationPossible" "AutomationPossible",
    "automationType" "AutomationType",
    "statusTicket" "StatusTicket",
    "createdAt" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "TicketMetadata_ticketId_fkey" FOREIGN KEY ("ticketId") REFERENCES "Ticket"(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "idx_User_companyId" ON "User"("companyId");
CREATE INDEX IF NOT EXISTS "idx_CompanyDataSourceApiKey_companyId" ON "CompanyDataSourceApiKey"("companyId");
CREATE INDEX IF NOT EXISTS "idx_CompanyDataSourceApiKey_source" ON "CompanyDataSourceApiKey"(source);
CREATE INDEX IF NOT EXISTS "idx_UserCredential_userId" ON "UserCredential"("userId");
CREATE INDEX IF NOT EXISTS "idx_RefreshToken_userId" ON "RefreshToken"("userId");
CREATE INDEX IF NOT EXISTS "idx_RefreshToken_token" ON "RefreshToken"(token);
CREATE INDEX IF NOT EXISTS "idx_Ticket_status" ON "Ticket"(status);
CREATE INDEX IF NOT EXISTS "idx_Ticket_team" ON "Ticket"(team);
CREATE INDEX IF NOT EXISTS "idx_Ticket_openDate" ON "Ticket"("openDate");
CREATE INDEX IF NOT EXISTS "idx_Ticket_companyId" ON "Ticket"("companyId");
CREATE INDEX IF NOT EXISTS "idx_Ticket_dataSourceApiKeyId" ON "Ticket"("dataSourceApiKeyId");
CREATE INDEX IF NOT EXISTS "idx_Invite_token" ON "Invite"(token);
CREATE INDEX IF NOT EXISTS "idx_Invite_companyId" ON "Invite"("companyId");
CREATE INDEX IF NOT EXISTS "idx_Invite_createdByUserId" ON "Invite"("createdByUserId");
CREATE INDEX IF NOT EXISTS "idx_TicketMetadata_ticketId" ON "TicketMetadata"("ticketId");
CREATE INDEX IF NOT EXISTS "idx_TicketMetadata_category" ON "TicketMetadata"(category);
