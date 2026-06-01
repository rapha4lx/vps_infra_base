-- Seed data (opcional)

INSERT INTO "Company" (id, name) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'Acme Corp');

INSERT INTO "User" (id, email, role, "companyId") VALUES
('550e8400-e29b-41d4-a716-446655440001', 'admin@acme.com', 'SITE_ADMIN', '550e8400-e29b-41d4-a716-446655440000');
