const state = {
  me: "",
  participants: [],
  selected: new Set(),
  month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  dirty: false,
};

const loginView = document.querySelector("#login-view");
const calendarView = document.querySelector("#calendar-view");
const loginForm = document.querySelector("#login-form");
const loginError = document.querySelector("#login-error");
const monthLabel = document.querySelector("#month-label");
const calendarGrid = document.querySelector("#calendar-grid");
const summary = document.querySelector("#calendar-summary");
const legend = document.querySelector("#legend");
const saveButton = document.querySelector("#save-button");
const previousButton = document.querySelector("#previous-month");
const nextButton = document.querySelector("#next-month");
const toast = document.querySelector("#toast");

const today = startOfDay(new Date());
const lastSelectableDay = new Date(today.getFullYear() + 1, today.getMonth(), today.getDate());
let toastTimer;

function startOfDay(value) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function dateKey(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isSameMonth(first, second) {
  return first.getFullYear() === second.getFullYear() && first.getMonth() === second.getMonth();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : {},
  });
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "The request failed.");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function showLogin() {
  loginView.hidden = false;
  calendarView.hidden = true;
  state.me = "";
  state.participants = [];
  state.selected = new Set();
  document.querySelector("#name").focus();
}

function openCalendar(payload) {
  state.me = payload.me;
  state.participants = payload.participants;
  const mine = state.participants.find(
    (participant) => participant.name.localeCompare(state.me, undefined, { sensitivity: "accent" }) === 0,
  );
  state.selected = new Set(mine?.dates || []);
  state.dirty = false;
  loginView.hidden = true;
  calendarView.hidden = false;
  document.querySelector("#signed-in-label").textContent = state.me;
  render();
}

function visibleParticipants() {
  return state.participants.map((participant) =>
    participant.name === state.me
      ? { ...participant, dates: [...state.selected] }
      : participant,
  );
}

function peopleForDate(key) {
  return visibleParticipants().filter((participant) => participant.dates.includes(key));
}

function colorIndex(name) {
  const ordered = visibleParticipants()
    .map((participant) => participant.name)
    .sort((first, second) => first.localeCompare(second));
  return ordered.indexOf(name) % 8;
}

function renderDay(value, outside) {
  const key = dateKey(value);
  const selectable = !outside && value >= today && value <= lastSelectableDay;
  const people = peopleForDate(key);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "calendar-day";
  button.setAttribute("role", "gridcell");
  button.setAttribute("aria-pressed", state.selected.has(key) ? "true" : "false");
  const dateName = value.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const availability = people.length ? ` Available: ${people.map((person) => person.name).join(", ")}.` : "";
  button.setAttribute("aria-label", `${dateName}.${availability}`);
  button.disabled = !selectable;
  if (outside) button.classList.add("is-outside");
  if (dateKey(value) === dateKey(today)) button.classList.add("is-today");
  if (state.selected.has(key)) button.classList.add("is-selected");

  const number = document.createElement("span");
  number.className = "day-number";
  number.textContent = value.getDate();
  button.append(number);

  if (people.length) {
    const count = document.createElement("span");
    count.className = "overlap-count";
    count.textContent = String(people.length);
    count.setAttribute("aria-hidden", "true");
    button.append(count);
  }

  const stripes = document.createElement("span");
  stripes.className = "stripe-stack";
  stripes.setAttribute("aria-hidden", "true");
  people.forEach((person) => {
    const stripe = document.createElement("span");
    stripe.className = `availability-stripe stripe-${colorIndex(person.name)}`;
    stripes.append(stripe);
  });
  button.append(stripes);

  if (selectable) {
    button.addEventListener("click", () => {
      if (state.selected.has(key)) state.selected.delete(key);
      else state.selected.add(key);
      state.dirty = true;
      render();
    });
  }
  return button;
}

function renderCalendar() {
  monthLabel.textContent = state.month.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
  calendarGrid.replaceChildren();
  const firstDay = new Date(state.month.getFullYear(), state.month.getMonth(), 1);
  const offset = (firstDay.getDay() + 6) % 7;
  const gridStart = new Date(firstDay);
  gridStart.setDate(firstDay.getDate() - offset);
  for (let index = 0; index < 42; index += 1) {
    const value = new Date(gridStart);
    value.setDate(gridStart.getDate() + index);
    calendarGrid.append(renderDay(value, !isSameMonth(value, state.month)));
  }

  const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const finalMonth = new Date(lastSelectableDay.getFullYear(), lastSelectableDay.getMonth(), 1);
  previousButton.disabled = state.month <= currentMonth;
  nextButton.disabled = state.month >= finalMonth;
}

function renderLegend() {
  legend.replaceChildren();
  const participants = visibleParticipants().sort((first, second) => first.name.localeCompare(second.name));
  participants.forEach((participant) => {
    const item = document.createElement("span");
    item.className = "legend-item";
    const mark = document.createElement("span");
    mark.className = `legend-mark stripe-${colorIndex(participant.name)}`;
    mark.setAttribute("aria-hidden", "true");
    const name = document.createElement("span");
    name.textContent = participant.name === state.me ? `${participant.name} (you)` : participant.name;
    item.append(mark, name);
    legend.append(item);
  });
}

function render() {
  renderCalendar();
  renderLegend();
  const participantCount = visibleParticipants().length;
  const selectedCount = state.selected.size;
  summary.textContent = `${participantCount} ${participantCount === 1 ? "boy" : "boys"} · ${selectedCount} of your dates selected`;
  saveButton.textContent = state.dirty ? "Save changes" : "Dates saved";
  saveButton.disabled = !state.dirty;
}

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 2600);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  const button = loginForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Opening…";
  const form = new FormData(loginForm);
  try {
    await api("/api/session", {
      method: "POST",
      body: JSON.stringify({ name: form.get("name"), pin: form.get("pin") }),
    });
    const payload = await api("/api/availability");
    loginForm.reset();
    openCalendar(payload);
  } catch (error) {
    loginError.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Open calendar";
  }
});

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  saveButton.textContent = "Saving…";
  try {
    const payload = await api("/api/availability", {
      method: "PUT",
      body: JSON.stringify({ dates: [...state.selected].sort() }),
    });
    state.participants = payload.participants;
    state.dirty = false;
    render();
    showToast("Your dates are saved.");
  } catch (error) {
    if (error.status === 401) showLogin();
    else showToast(error.message);
  }
});

previousButton.addEventListener("click", () => {
  state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1);
  renderCalendar();
});

nextButton.addEventListener("click", () => {
  state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1);
  renderCalendar();
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
  } finally {
    showLogin();
  }
});

api("/api/availability").then(openCalendar).catch(showLogin);
