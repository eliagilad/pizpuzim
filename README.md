# pizpuzim

A personal assistant built with LangGraph. The long-term aim is a Telegram bot that helps with everyday tasks. This repository is the foundation: one long-running service, a typed agent graph, Gmail, Google Calendar, and saved group history.

There is no reminder system and no confirmation step before calendar writes. Those are later work.

## Architecture

`pizpuzim` is the service. While it is running it listens to Telegram, saves group text, calls the agent, and uses Gmail and Calendar when the model asks.

1. A text message arrives in a group or supergroup.
2. The service stores it in `data/history.sqlite`.
3. It loads the newest 40 messages from that chat, with each sender's name, and passes them to the LangGraph workflow.
4. The agent node calls an OpenAI chat model. If the model requests a tool, a tool node runs it and the agent node runs again.
5. The reply is sent to the same group and stored in the history.

The graph state is the `messages` list for that turn. History survives restarts because it lives in SQLite. The Bot API cannot download messages from before the service started, so history begins with the first message the running service receives.

Email and calendar text is data. The system prompt tells the model that instructions inside an email or event must not change its behavior or authorize an action. Tool results are returned as plain text, not as new system messages.

```
Telegram group message
        |
        v
  LangGraph workflow
   agent <-> tools
        |
        +-- Gmail (read, search, threads)
        +-- Google Calendar (list, create, update, delete events)
        |
        v
  Reply in the same group
```

| Path | Role |
|---|---|
| `src/service.py` | The process you run. It owns login, history, the graph, and Telegram polling |
| `src/history.py` | SQLite log of group text and assistant replies |
| `src/agent/` | Typed state, system prompt, and the compiled graph |
| `src/integrations/google/` | OAuth and the Gmail and Calendar API clients |
| `src/integrations/telegram/` | Turns a group update into a graph call |
| `src/tools/` | Tools the model is allowed to call |
| `tests/` | Unit tests with fake models and fake API clients |
| `secrets/` | Local OAuth client file and token file. Gitignored |
| `data/` | Group history database. Gitignored |

## Roadmap

**Phase 1.** Project layout, environment configuration, a LangGraph workflow with typed state, OpenAI via environment variables, error handling, and tests.

**Phase 2.** Google OAuth, Gmail search and read, event management on calendars the user can access, then those tools attached to the graph.

**Phase 3.** One service process. It stores group text, answers with that history in context, and keeps running until you stop it.

**Later.** Reminders and schedules, more tools, and a confirmation step before any action that changes Google data.

## Setup

Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in `.env` locally. Do not commit it.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Chat model name passed to `ChatOpenAI`. Default `gpt-4.1-mini` |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `GOOGLE_CREDENTIALS_PATH` | OAuth desktop-client JSON. Default `secrets/credentials.json` |
| `GOOGLE_TOKEN_PATH` | Saved user token. Default `secrets/token.json` |
| `HISTORY_PATH` | SQLite file for group history. Default `data/history.sqlite` |

## Google Cloud

1. Create or select a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the Gmail API and the Google Calendar API.
3. Configure the OAuth consent screen. Add the Gmail readonly scope and the Calendar scope below. While the app is in testing, add your Google account as a test user.
4. Create an OAuth client of type Desktop app. If the console asks whether the client is for an AI agent, create a separate client for that use.
5. Download the client JSON and save it at `secrets/credentials.json`.

Scopes used:

- `https://www.googleapis.com/auth/gmail.readonly` for search, metadata, message bodies, and threads. The agent cannot send, delete, or relabel mail.
- `https://www.googleapis.com/auth/calendar` for listing calendars and listing, creating, updating, and deleting events. Sharing settings and calendar ACLs are out of scope.

Sign in once, or let the service open the browser on its first run when `secrets/credentials.json` is already in place:

```bash
pizpuzim --login
```

A browser window opens. On success the refresh token is written to `secrets/token.json`. Later runs refresh an expired access token without opening the browser. If refresh fails, run the login command again.

## Run the service

From the project directory, with the virtualenv active:

```bash
pizpuzim
```

That process is the whole assistant. It signs in to Google when the client file exists and a token is still needed, opens the history database, builds the agent, and long-polls Telegram until you stop it. Polling and a webhook cannot be active at the same time.

The bot answers text messages in groups and supergroups. It ignores private chats, channels, and messages from other bots. A repeated Telegram update for a message it already stored does not get a second reply.

Privacy mode is off for this bot. Telegram still hides ordinary messages in groups the bot joined before that change. Remove the bot from each of those groups and add it again. New groups pick up the privacy setting immediately.

## Development

```bash
pytest
```

Tests do not call OpenAI, Google, or Telegram. They use stand-ins for the model and the API clients.

Live checks, after `.env` exists:

```bash
pizpuzim --login
pizpuzim
```

Then send a text message in a group that contains the bot. The reply can use earlier messages from that group that arrived while the service was running.

## Security

- Secrets stay in `.env`, `secrets/credentials.json`, and `secrets/token.json`. Group history stays in `data/`. All of these are gitignored.
- Logs record the chat id, the update id, and the exception type. They do not record the bot token, OAuth tokens, message bodies, or email content.
- If the agent fails, the chat receives a fixed sentence and not the exception text.
- Content from Gmail and Calendar is untrusted. It cannot replace the system prompt.
