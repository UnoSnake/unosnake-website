export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Test de connexion du Worker
    if (url.pathname === "/api/test") {
      return new Response(
        JSON.stringify({
          ok: true,
          worker: "UnoSnake",
          amazonCredentialId: Boolean(env.AMAZON_CREDENTIAL_ID),
          amazonCredentialSecret: Boolean(env.AMAZON_CREDENTIAL_SECRET),
        }),
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    // Tout le reste continue d'être servi par le site statique
    return env.ASSETS.fetch(request);
  },
};
