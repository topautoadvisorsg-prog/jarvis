# Jarvis personal Gmail and Calendar read-only connector

Date: 2026-09-30

## Boundary

This connector is for Buddy's personal Gmail and Calendar. It is separate from
SmartKlix business outreach and cannot send or modify email, create or modify
calendar events, access Drive, access Contacts, spend money, or execute CRM work.

It requests exactly:

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/calendar.readonly`

The connector refuses a token carrying a different scope set. Email bodies and
calendar descriptions are returned as untrusted data and never treated as agent
instructions. Searches, result counts, body length, and event descriptions are
bounded.

## Implemented tools

- `get_personal_google_status`
- `search_personal_gmail`
- `read_personal_gmail_message`
- `list_personal_calendar_events`

The MCP server is safe to enable before OAuth. Until setup is complete, it
returns `setup_required`/`unavailable` without opening a consent flow.

## Pending Buddy setup

1. In a Buddy-controlled Google Cloud project, enable Gmail API and Google
   Calendar API.
2. Configure the OAuth consent screen for the intended personal account/test
   user.
3. Create a **Desktop app** OAuth client and download its JSON.
4. Store it without committing it:

   ```bash
   python /home/jovan/.hermes/jarvis-hud/integrations/google_readonly_auth.py \
     --client-secret /path/to/client_secret.json
   ```

5. Generate the authorization URL:

   ```bash
   python /home/jovan/.hermes/jarvis-hud/integrations/google_readonly_auth.py --auth-url
   ```

6. Open that URL, approve only the two displayed read-only scopes, then copy
   the complete failed `http://localhost:1/?code=...&state=...` redirect URL.
7. Exchange it locally:

   ```bash
   python /home/jovan/.hermes/jarvis-hud/integrations/google_readonly_auth.py \
     --auth-code 'PASTE_COMPLETE_REDIRECT_URL'
   ```

Credential files live under `~/.hermes/jarvis-google-readonly/`, use mode 0600,
and are excluded from Git. The existing broad `~/.hermes/google_token.json` is
not reused.

## Acceptance after OAuth

1. Status returns `ready` and exactly two read-only scopes.
2. Search a bounded Gmail query and read one known message.
3. List the next seven days of the primary calendar.
4. Confirm the MCP surface contains no send, reply, label, delete, create,
   update, Drive, Contacts, Sheets, or Docs tool.
5. Restart the gateway and repeat status plus one Gmail/Calendar read.
