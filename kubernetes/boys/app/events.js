const eventList = document.querySelector("#event-list");
const eventEmpty = document.querySelector("#event-empty");
const eventError = document.querySelector("#event-error");

function eventAction(event) {
  if (event.action === "claimed" || (event.action === "baseline" && event.days === 0)) {
    return "Закрепил имя";
  }
  if (event.days === 0) return "Убрал отметки свободных дней";
  return `Отметил свободных дней: ${event.days}`;
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
    time.textContent = "До начала истории";
  } else {
    time.dateTime = event.at;
    time.textContent = new Intl.DateTimeFormat("ru-RU", {
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
    if (!response.ok) throw new Error(payload.error || "Не удалось загрузить историю.");
    eventList.replaceChildren(...payload.events.map(renderEvent));
    eventEmpty.hidden = payload.events.length !== 0;
  } catch (error) {
    eventError.textContent = "Не удалось загрузить историю. Повторим попытку автоматически.";
  }
}

loadEvents();
setInterval(loadEvents, 5000);
