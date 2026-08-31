export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // ---------------------------------------------------------
    // AMAZON TEST
    // /api/amazon-test
    // ---------------------------------------------------------
    if (url.pathname === "/api/amazon-test") {
      try {
        if (!env.AMAZON_CREDENTIAL_ID || !env.AMAZON_CREDENTIAL_SECRET) {
          return json({
            ok: false,
            error: "Amazon credentials are missing in Cloudflare."
          }, 500);
        }

        // 1. Get OAuth access token
        const tokenResponse = await fetch(
          "https://api.amazon.co.uk/auth/o2/token",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              grant_type: "client_credentials",
              client_id: env.AMAZON_CREDENTIAL_ID,
              client_secret: env.AMAZON_CREDENTIAL_SECRET,
              scope: "creatorsapi::default"
            })
          }
        );

        const tokenData = await tokenResponse.json();

        if (!tokenResponse.ok || !tokenData.access_token) {
          return json({
            ok: false,
            step: "oauth",
            status: tokenResponse.status,
            error: tokenData
          }, 500);
        }

        // 2. Search Amazon France
        const amazonResponse = await fetch(
          "https://creatorsapi.amazon/catalog/v1/searchItems",
          {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${tokenData.access_token}`,
              "Content-Type": "application/json",
              "x-marketplace": "www.amazon.fr"
            },
            body: JSON.stringify({
              partnerTag: "unosnake09-21",
              marketplace: "www.amazon.fr",
              keywords: "déco scandinave maison",
              searchIndex: "HomeAndKitchen",
              itemCount: 5,
              languagesOfPreference: ["fr_FR"],
              resources: [
                "images.primary.large",
                "itemInfo.title",
                "itemInfo.byLineInfo",
                "itemInfo.classifications",
                "offersV2.listings.price",
                "offersV2.listings.availability"
              ]
            })
          }
        );

        const amazonData = await amazonResponse.json();

        if (!amazonResponse.ok) {
          return json({
            ok: false,
            step: "amazon-search",
            status: amazonResponse.status,
            error: amazonData
          }, 500);
        }

        // 3. Normalize products
        const items = amazonData?.searchResult?.items || [];

        const products = items.map(item => ({
          asin: item.asin || null,
          title:
            item?.itemInfo?.title?.displayValue || null,
          brand:
            item?.itemInfo?.byLineInfo?.brand?.displayValue || null,
          category:
            item?.itemInfo?.classifications?.productGroup?.displayValue || null,
          image:
            item?.images?.primary?.large?.url || null,
          price:
            item?.offersV2?.listings?.[0]?.price?.money?.amount ?? null,
          currency:
            item?.offersV2?.listings?.[0]?.price?.money?.currency ?? "EUR",
          availability:
            item?.offersV2?.listings?.[0]?.availability?.type || null,
          amazonUrl:
            item.detailPageURL || null
        }));

        return json({
          ok: true,
          marketplace: "www.amazon.fr",
          keyword: "déco scandinave maison",
          count: products.length,
          products
        });

      } catch (error) {
        return json({
          ok: false,
          error: error.message
        }, 500);
      }
    }

    // ---------------------------------------------------------
    // NORMAL WEBSITE
    // ---------------------------------------------------------
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    return new Response(
      "UnoSnake Worker actif.",
      {
        status: 200,
        headers: {
          "Content-Type": "text/plain; charset=UTF-8"
        }
      }
    );
  }
};

function json(data, status = 200) {
  return new Response(
    JSON.stringify(data, null, 2),
    {
      status,
      headers: {
        "Content-Type": "application/json; charset=UTF-8"
      }
    }
  );
}
