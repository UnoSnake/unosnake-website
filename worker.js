export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Test de connexion Amazon
    if (url.pathname === "/api/test") {
      return new Response(
        JSON.stringify({
          ok: true,
          worker: "UnoSnake",
          amazonCredentialId: Boolean(env.AMAZON_CREDENTIAL_ID),
          amazonCredentialSecret: Boolean(env.AMAZON_CREDENTIAL_SECRET)
        }),
        {
          headers: {
            "Content-Type": "application/json"
          }
        }
      );
    }

    // Laisser Cloudflare servir les fichiers du site
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    // Sécurité : si les assets ne sont pas encore liés,
    // on affiche une erreur claire au lieu de planter.
    return new Response(
      "UnoSnake est en cours de configuration. Le binding ASSETS n'est pas encore disponible.",
      {
        status: 503,
        headers: {
          "Content-Type": "text/plain; charset=UTF-8"
        }
      }
    );
  }
};
