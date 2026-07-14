# LanguageTool setup

The `check-markdown` skill runs LanguageTool through textlint's
`@textlint-rule/gramma` rule, which POSTs to a LanguageTool HTTP endpoint's
`/v2/check`. The runner ([`../scripts/check-md.mjs`](../scripts/check-md.mjs)) resolves
the endpoint in this order:

1. `LANGUAGETOOL_URL` environment variable, else
2. the default `http://localhost:8081/v2/check`.

If that endpoint is unreachable, the runner tries to start a local Docker server; if that
also fails it drops the grammar rule and continues with textlint + Vale. So LanguageTool
is "on by default" but never blocks a run.

## Option A — Docker (default, zero config)

The community image listens on container port **8010**. Map it to the host port in your
endpoint (default `8081`):

```sh
docker run -d --rm -p 8081:8010 erikvl87/languagetool
```

The runner does exactly this automatically when Docker is available and no server answers.
Stop it with `docker ps` + `docker stop <id>`.

## Option B — Local JAR (no Docker)

Download `LanguageTool-stable.zip` from <https://languagetool.org/download/>, unzip, then:

```sh
java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin '*'
```

```powershell
java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin '*'
```

Needs Java 17+. Add `-Xmx2G` for large documents.

## Public API — not used by default (privacy)

The runner never sends text off-box on its own: it only talks to `localhost`, and if no
local server is reachable it drops grammar checks rather than reach out to the internet.

You *can* force the hosted API by setting `LANGUAGETOOL_URL` to a remote host — but then
your document text is sent to that server, and the runner prints a warning to make that
explicit:

```sh
export LANGUAGETOOL_URL=https://api.languagetool.org/v2/check   # sends text to LanguageTool's servers
```

Prefer a local server (Options A/B). The free hosted tier is also rate-limited
(20 requests/min, 20,000 characters/request) and LanguageTool asks that automated/bulk use
self-host.

## Verifying a server

```sh
curl -X POST --data-urlencode 'language=en-US' --data-urlencode 'text=She go to school.' \
  http://localhost:8081/v2/check
```

A JSON response with a `matches` array means the server is up.

## LaTeX

For grammar checking on `.tex`, see the [`check-tex`](../../check-tex/SKILL.md) skill —
`@textlint-rule/gramma` crashes on the LaTeX AST, so LaTeX uses
[`ltex-cli`](https://github.com/valentjn/ltex-ls) (LanguageTool with a native LaTeX parser)
instead.
