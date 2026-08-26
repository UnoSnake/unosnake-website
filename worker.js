export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // ─────────────────────────────────────────────
    // API TEST
    // ─────────────────────────────────────────────
    if (url.pathname === "/api/test") {
      return new Response(
        JSON.stringify({
          ok: true,
          worker: "UnoSnake",
          amazonCredentialId: Boolean(env.AMAZON_CREDENTIAL_ID),
          amazonCredentialSecret: Boolean(env.AMAZON_CREDENTIAL_SECRET),
          assetsBinding: Boolean(env.ASSETS)
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json; charset=utf-8"
          }
        }
      );
    }

    // ─────────────────────────────────────────────
    // SITE STATIQUE
    // ─────────────────────────────────────────────
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    // ─────────────────────────────────────────────
    // ERREUR CLAIRE SI LE BINDING MANQUE
    // ─────────────────────────────────────────────
    return new Response(
      "UnoSnake est en cours de configuration : le binding ASSETS n'est pas disponible.",
      {
        status: 503,
        headers: {
          "Content-Type": "text/plain; charset=utf-8"
        }
      }
    );
  }
};
