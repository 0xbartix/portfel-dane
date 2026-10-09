// Budzik serwisu danych (Cloudflare Worker, użytkownik 2026-10-09). Harmonogram dane-api w GitHubie ma
// uruchamiać się co godzinę, ale GitHub uruchamiał go ok. 4 razy na dobę – kurs NBP z 12:15 trafiał do zeszytów
// dopiero wieczorem. Worker co godzinę (47. minuta, z dala od 17. minuty GitHuba) uruchamia przebieg ręcznie.
// Sekret GH_TOKEN: token fine-grained tylko do repozytorium portfel-dane, uprawnienie Actions: read and write.
const ACTIONS = "https://api.github.com/repos/0xbartix/portfel-dane/actions";
const WORKFLOW = "dane-api.yml";

export async function obudz(env, fetchFn = fetch) {
  const naglowki = {
    Authorization: `Bearer ${env.GH_TOKEN}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "portfel-budzik",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  // przebieg czekający w kolejce pracowałby na wersji danych sprzed trwającego – jego zapis by się nie udał
  for (const status of ["in_progress", "queued"]) {
    const r = await fetchFn(`${ACTIONS}/workflows/${WORKFLOW}/runs?status=${status}&per_page=1`, { headers: naglowki });
    if (!r.ok) throw new Error(`GitHub ${r.status}: ${await r.text()}`);
    if ((await r.json()).total_count > 0) return `pominięty – przebieg już ${status === "queued" ? "czeka" : "trwa"}`;
  }
  const r = await fetchFn(`${ACTIONS}/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { ...naglowki, "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main" }),
  });
  if (!r.ok) throw new Error(`GitHub ${r.status}: ${await r.text()}`);
  return "uruchomiony";
}

export default {
  async scheduled(event, env, ctx) {
    if (!env.GH_TOKEN) throw new Error("brak sekretu GH_TOKEN – dodaj go w ustawieniach Workera");
    console.log(await obudz(env));
  },
};
