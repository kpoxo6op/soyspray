"use strict";

const cards = document.querySelector("#cards");
const notice = document.querySelector("#notice");
const refresh = document.querySelector("#refresh");
const blocked = document.querySelector("#blocked");
const money = new Intl.NumberFormat("en-NZ", { style: "currency", currency: "NZD" });

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function showNotice(message, state = "") {
  notice.className = `notice ${state}`.trim();
  notice.textContent = message;
}

function renderTrace(payload) {
  const trace = payload.trace || {};
  const headers = trace.headers || {};
  document.querySelector("#trace-status").textContent = trace.status || "-";
  document.querySelector("#trace-correlation").textContent =
    headers["x-banklab-correlation-id"] || trace.request_id || "-";
  document.querySelector("#trace-rate").textContent = headers["ratelimit-remaining"] || "-";
  document.querySelector("#trace-time").textContent = trace.elapsed_ms ? `${trace.elapsed_ms} ms` : "-";
}

function paymentCard(item) {
  const article = element("article", "payment-card");
  const identity = element("div");
  identity.append(
    element("div", "card-name", item.name),
    element("div", "card-number", `•••• •••• •••• ${item.last4}`),
  );
  const meta = element("div", "card-meta");
  meta.append(
    element("span", "", item.status),
    element("span", "", `Available ${money.format(item.available)}`),
  );
  article.append(identity, meta);
  return article;
}

function renderCards(payload) {
  renderTrace(payload);
  const items = payload.data?.cards || [];
  if (!payload.ok || items.length === 0) {
    cards.replaceChildren(element("div", "empty", "Cards are unavailable right now."));
    showNotice(payload.message || "The gateway did not return the card list.", "bad");
    return;
  }
  cards.replaceChildren(...items.map(paymentCard));
  showNotice("Cards refreshed through Kong.", "good");
}

async function load(path, renderer, button) {
  button.disabled = true;
  cards.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(path, { cache: "no-store" });
    renderer(await response.json());
  } catch (error) {
    showNotice(`The lab request failed: ${error.message}`, "bad");
  } finally {
    cards.setAttribute("aria-busy", "false");
    button.disabled = false;
  }
}

refresh.addEventListener("click", () => load("/api/cards", renderCards, refresh));
blocked.addEventListener("click", () => load("/api/cards/without-key", (payload) => {
  renderTrace(payload);
  showNotice(
    payload.expected_rejection
      ? "Kong blocked the request because it had no app credential."
      : "The no-credential check did not return the expected rejection.",
    payload.expected_rejection ? "good" : "bad",
  );
}, blocked));

load("/api/cards", renderCards, refresh);
