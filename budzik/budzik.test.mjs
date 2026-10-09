// node --test api/budzik – budzik serwisu danych (Cloudflare Worker), bez sieci: fetch podmieniony.
import { test } from "node:test";
import assert from "node:assert/strict";
import budzik, { obudz } from "./budzik.js";

function github({ trwa = 0, wKolejce = 0, dispatch = 204 } = {}) {
  const wywolania = [];
  const fetchFn = async (url, opcje = {}) => {
    wywolania.push({ url, ...opcje });
    if (url.includes("status=in_progress")) return Response.json({ total_count: trwa });
    if (url.includes("status=queued")) return Response.json({ total_count: wKolejce });
    return new Response(null, { status: dispatch });
  };
  return { fetchFn, wywolania };
}

test("uruchamia aktualizację danych na gałęzi main z tokenem", async () => {
  const { fetchFn, wywolania } = github();
  assert.equal(await obudz({ GH_TOKEN: "t" }, fetchFn), "uruchomiony");
  const post = wywolania.at(-1);
  assert.equal(post.url, "https://api.github.com/repos/0xbartix/portfel-dane/actions/workflows/dane-api.yml/dispatches");
  assert.equal(post.method, "POST");
  assert.deepEqual(JSON.parse(post.body), { ref: "main" });
  assert.equal(post.headers.Authorization, "Bearer t");
  assert.ok(post.headers["User-Agent"]);
});

test("pomija, gdy przebieg trwa albo czeka – oczekujący zapisałby dane na starej wersji", async () => {
  for (const stan of [{ trwa: 1 }, { wKolejce: 1 }]) {
    const { fetchFn, wywolania } = github(stan);
    assert.match(await obudz({ GH_TOKEN: "t" }, fetchFn), /pominięty/);
    assert.ok(wywolania.every((w) => w.method !== "POST"));
  }
});

test("błąd GitHuba (np. wygasły token) kończy się wyjątkiem – widać go w logach Workera", async () => {
  const { fetchFn } = github({ dispatch: 401 });
  await assert.rejects(obudz({ GH_TOKEN: "t" }, fetchFn), /GitHub 401/);
});

test("bez sekretu GH_TOKEN nie wysyła niczego", async () => {
  await assert.rejects(budzik.scheduled({}, {}, {}), /GH_TOKEN/);
});
