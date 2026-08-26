export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // =========================
    // TEST API
    // =========================
    if (url.pathname === "/api/test") {
      return new Response(
        JSON.stringify(
          {
            ok: true,
            worker: "UnoSnake",
            amazonCredentialId: Boolean(env.AMAZON_CREDENTIAL_ID),
            amazonCredentialSecret: Boolean(
              env.AMAZON_CREDENTIAL_SECRET
            )
          },
          null,
          2
        ),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json; charset=UTF-8",
            "Cache-Control": "no-store"
          }
        }
      );
    }

    // =========================
    // SITE WEB
    // =========================
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    // =========================
    // ERREUR DE CONFIGURATION
    // =========================
    return new Response(
      "UnoSnake : le binding ASSETS n'est pas disponible.",
      {
        status: 503,
        headers: {
          "Content-Type": "text/plain; charset=UTF-8"
        }
      }
    );
  }
};
