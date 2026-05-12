/**
 * Netlify function: admin-invite
 * Thin proxy that forwards invite-send requests to the Nexus backend.
 *
 * Security model:
 *  - Requires a valid Supabase JWT from the logged-in admin
 *  - Adds X-Admin-Token server-side (never exposed to browser)
 *  - Backend sends email using its own SMTP credentials (not Netlify's)
 *  - No email credentials stored in Netlify
 *
 * Environment variables required on Netlify:
 *  NEXUS_API_URL            — public URL of Nexus control center backend
 *  CONTROL_CENTER_ADMIN_TOKEN — forwarded as X-Admin-Token to backend
 */

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
      body: '',
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  // Require Supabase JWT from logged-in admin user
  const authHeader = event.headers?.authorization || event.headers?.Authorization || '';
  if (!authHeader.startsWith('Bearer ')) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Unauthorized — admin JWT required' }) };
  }

  const NEXUS_URL = (process.env.NEXUS_API_URL || 'http://localhost:4000').replace(/\/$/, '');
  const ADMIN_TOKEN = process.env.CONTROL_CENTER_ADMIN_TOKEN || '';

  if (!ADMIN_TOKEN) {
    console.error('admin-invite: CONTROL_CENTER_ADMIN_TOKEN not configured');
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Backend admin token not configured on server.' }),
    };
  }

  let reqBody;
  try {
    reqBody = event.body || '{}';
    JSON.parse(reqBody); // validate JSON
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid request body' }) };
  }

  try {
    const upstream = await fetch(`${NEXUS_URL}/api/admin/tester-invites/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': ADMIN_TOKEN,
      },
      body: reqBody,
      signal: AbortSignal.timeout(15000),
    });

    const responseBody = await upstream.text();
    console.log(`admin-invite: backend responded ${upstream.status}`);

    return {
      statusCode: upstream.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: responseBody,
    };
  } catch (err) {
    console.error('admin-invite: backend unreachable:', err.message);
    return {
      statusCode: 502,
      body: JSON.stringify({ error: 'Nexus backend unreachable', detail: err.message }),
    };
  }
};
