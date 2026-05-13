-- Grants Catalog Seed — Verified public grant programs
-- Run via: supabase db query --linked -f supabase/seeds/grants_catalog_seed.sql

INSERT INTO public.grants_catalog (title, grantor, category, amount_min, amount_max, deadline, official_url, eligibility, is_active)
VALUES
  (
    'SBIR Phase I — Small Business Innovation Research',
    'Multiple Federal Agencies (DOD, NIH, NSF, DOE, NASA)',
    'federal',
    50000, 275000,
    NULL,
    'https://www.sbir.gov',
    'US for-profit small businesses, <500 employees, >50% US-owned. Tech/research innovation focus.',
    true
  ),
  (
    'STTR Phase I — Small Business Technology Transfer',
    'Multiple Federal Agencies (NIH, NSF, DOD, DOE, NASA)',
    'federal',
    150000, 275000,
    NULL,
    'https://www.sbir.gov/about/about-sttr',
    'For-profit small business with research institution partner. Joint research agreement required.',
    true
  ),
  (
    'NASE Growth Grant',
    'National Association for the Self-Employed (NASE)',
    'nonprofit',
    0, 4000,
    NULL,
    'https://www.nase.org/benefits/business-resources/nase-growth-grants',
    'NASE members; small businesses and micro-businesses. Membership ~$14/month.',
    true
  ),
  (
    'Amber Grant for Women',
    'WomensNet',
    'nonprofit',
    10000, 25000,
    NULL,
    'https://ambergrantsforwomen.com',
    'Women-owned businesses at any stage. Monthly award + annual $25K award.',
    true
  ),
  (
    'Comcast RISE Investment Fund',
    'Comcast NBCUniversal',
    'business',
    10000, 10000,
    NULL,
    'https://rise.comcast.com',
    'Small businesses owned by people of color; 3+ years in operation; select states.',
    true
  ),
  (
    'Hello Alice Small Business Grant',
    'Hello Alice (Corporate Sponsors)',
    'business',
    5000, 25000,
    NULL,
    'https://helloalice.com/grants',
    'Small businesses; multiple programs by type, industry, and demographic. Complete Hello Alice profile first.',
    true
  ),
  (
    'FedEx Small Business Grant Contest',
    'FedEx',
    'business',
    10000, 50000,
    NULL,
    'https://smallbusiness.fedex.com/grant-contest.html',
    'US for-profit small businesses with fewer than 99 employees. Annual contest, video pitch required.',
    true
  ),
  (
    'SBA 8(a) Business Development Program',
    'U.S. Small Business Administration',
    'federal',
    0, 0,
    NULL,
    'https://www.sba.gov/federal-contracting/contracting-assistance-programs/8a-business-development-program',
    'Socially and economically disadvantaged business owners; 51%+ minority-owned. Access to set-aside federal contracts.',
    true
  ),
  (
    'MBDA Business Development Programs',
    'Minority Business Development Agency / U.S. Dept of Commerce',
    'federal',
    0, 0,
    NULL,
    'https://www.mbda.gov',
    'Minority-owned businesses (African American, Hispanic, Asian, Native American, etc.).',
    true
  ),
  (
    'USDA Rural Business Development Grant',
    'USDA Rural Development',
    'federal',
    0, 500000,
    NULL,
    'https://www.rd.usda.gov/programs-services/business-programs/rural-business-development-grants',
    'Rural small businesses in towns with population under 50,000.',
    true
  ),
  (
    'Digital Undivided Breakthrough Black Women Founders Grant',
    'Digital Undivided',
    'nonprofit',
    5000, 5000,
    NULL,
    'https://www.digitalundivided.com',
    'Black women-owned startups and businesses.',
    true
  ),
  (
    'SBA Community Advantage Loan Program',
    'U.S. Small Business Administration (via approved lenders)',
    'federal',
    0, 350000,
    NULL,
    'https://www.sba.gov/funding-programs/loans/7a-loans/sba-community-advantage-loans',
    'Underserved market businesses, low-to-moderate income areas. Loan program (not pure grant).',
    true
  )
ON CONFLICT DO NOTHING;
