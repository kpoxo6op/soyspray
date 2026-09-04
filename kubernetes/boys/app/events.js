const eventList = document.querySelector("#event-list");
const eventEmpty = document.querySelector("#event-empty");
const eventError = document.querySelector("#event-error");

function eventAction(event) {
  if (event.action === "claimed" || (event.action === "baseline" && event.days === 0)) {
    return "Claimed name";
  }
  if (event.days === 0) return "Cleared available days";
  return `Set ${event.days} available ${event.days === 1 ? "day" : "days"}`;
}

function renderEvent(event) {
  const item = document.createElement("li");
  item.className = "event-item";

  const name = document.createElement("span");
  name.className = "event-name";
  name.textContent = event.name;

  const action = document.createElement("span");
  action.className = "event-action";
  action.textContent = eventAction(event);

  const time = document.createElement(event.action === "baseline" ? "span" : "time");
  time.className = "event-time";
  if (event.action === "baseline") {
    time.textContent = "Before log";
  } else {
    time.dateTime = event.at;
    time.textContent = new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(event.at));
  }

  item.append(name, action, time);
  return item;
}

async function loadEvents() {
  try {
    const response = await fetch("/api/events", { credentials: "same-origin" });
    if (response.status === 401) {
      window.location.replace("/");
      return;
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load events.");
    eventList.replaceChildren(...payload.events.map(renderEvent));
    eventEmpty.hidden = payload.events.length !== 0;
  } catch (error) {
    eventError.textContent = error.message;
  }
}

loadEvents();
setInterval(loadEvents, 5000);
