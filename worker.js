export default {
  async fetch(request, env) {
    return new Response("WORKER UNO SNAKE OK", {
      status: 200,
      headers: {
        "Content-Type": "text/plain"
      }
    });
  }
};
