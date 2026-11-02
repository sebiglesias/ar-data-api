/**
 * Cloudflare Worker Gateway for RapidAPI -> GitHub Pages Static JSON API
 * Validates X-RapidAPI-Proxy-Secret and serves cached JSON endpoints with sub-20ms edge latency.
 *
 * Environment Variable required in Cloudflare Worker Settings:
 * - RAPIDAPI_PROXY_SECRET: Your unique secret from RapidAPI Studio -> Gateway Settings
 */
const ORIGIN_BASE = "https://sebiglesias.com.ar/ar-data-api";

const ENDPOINT_MAP = {
  "/": "/v1/all.json",
  "/v1": "/v1/all.json",
  "/v1/all": "/v1/all.json",
  "/v1/all.json": "/v1/all.json",
  "/v1/dolar": "/v1/dolar.json",
  "/v1/dolar.json": "/v1/dolar.json",
  "/v1/inflacion": "/v1/inflacion.json",
  "/v1/inflacion.json": "/v1/inflacion.json",
  "/v1/monotributo": "/v1/monotributo.json",
  "/v1/monotributo.json": "/v1/monotributo.json",
  "/v1/unidades-legales": "/v1/unidades-legales.json",
  "/v1/unidades-legales.json": "/v1/unidades-legales.json",
  "/v1/feriados": "/v1/feriados.json",
  "/v1/feriados.json": "/v1/feriados.json"
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-RapidAPI-Key, X-RapidAPI-Host, X-RapidAPI-Proxy-Secret"
        }
      });
    }

    // Verify RapidAPI Proxy Secret when configured in Cloudflare Worker env
    if (env.RAPIDAPI_PROXY_SECRET) {
      const incomingSecret = request.headers.get("X-RapidAPI-Proxy-Secret");
      if (incomingSecret !== env.RAPIDAPI_PROXY_SECRET) {
        return new Response(
          JSON.stringify({
            error: "Unauthorized",
            message: "Direct access disabled. Subscribe via RapidAPI Hub or use valid X-RapidAPI-Proxy-Secret."
          }),
          {
            status: 401,
            headers: { "Content-Type": "application/json; charset=utf-8" }
          }
        );
      }
    }

    const url = new URL(request.url);
    const cleanPath = url.pathname.replace(/\/+$/, "") || "/";
    const targetFile = ENDPOINT_MAP[cleanPath];

    if (!targetFile) {
      return new Response(
        JSON.stringify({
          error: "Not Found",
          available_endpoints: Object.keys(ENDPOINT_MAP).filter(k => !k.endsWith(".json") && k !== "/")
        }),
        {
          status: 404,
          headers: { "Content-Type": "application/json; charset=utf-8" }
        }
      );
    }

    const upstreamRes = await fetch(`${ORIGIN_BASE}${targetFile}`, {
      cf: { cacheTtl: 300, cacheEverything: true }
    });

    const body = await upstreamRes.text();
    return new Response(body, {
      status: upstreamRes.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=300, s-maxage=300",
        "X-Powered-By": "ar-data-api"
      }
    });
  }
};
