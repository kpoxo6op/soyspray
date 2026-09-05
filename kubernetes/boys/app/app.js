const state = {
  crew: [],
  member: null,
  claimSeedPin: "",
  me: "",
  participants: [],
  selected: new Set(),
  month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  dirty: false,
  saved: new Set(),
  revision: "",
  saving: false,
  generation: 0,
  conflict: null,
  saveError: "",
  refreshing: false,
};

const participantColorClasses = {
  "Boris K": "boy-boris-k",
  "Sergey Kiktev": "boy-sergey-kiktev",
  "Max Edin": "boy-max-edin",
  "Innok Mikhalev": "boy-innok-mikhalev",
  "Alexey Pichulev": "boy-alexey-pichulev",
  "Vitaly Borisov": "boy-vitaly-borisov",
  "Eugene Kobyak": "boy-eugene-kobyak",
  "Konstantin Pastbin": "boy-konstantin-pastbin",
  "Bronislav": "boy-bronislav",
};

const accessView = document.querySelector("#access-view");
const calendarView = document.querySelector("#calendar-view");
const nameForm = document.querySelector("#name-form");
const loginForm = document.querySelector("#login-form");
const crewPinForm = document.querySelector("#crew-pin-form");
const personalPinForm = document.querySelector("#personal-pin-form");
const accessForms = [nameForm, loginForm, crewPinForm, personalPinForm];
const accessTitle = document.querySelector("#access-title");
const accessInstruction = document.querySelector("#access-instruction");
const nameSelect = document.querySelector("#name");
const loginUsername = document.querySelector("#login-username");
const claimUsername = document.querySelector("#claim-username");
const nameError = document.querySelector("#name-error");
const loginError = document.querySelector("#login-error");
const crewPinError = document.querySelector("#crew-pin-error");
const personalPinError = document.querySelector("#personal-pin-error");
const monthLabel = document.querySelector("#month-label");
const calendarGrid = document.querySelector("#calendar-grid");
const summary = document.querySelector("#calendar-summary");
const legend = document.querySelector("#legend");
const saveButton = document.querySelector("#save-button");
const saveStatus = document.querySelector("#save-status");
const conflictPanel = document.querySelector("#save-conflict");
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
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      signal: controller.signal,
      headers: options.body ? { "Content-Type": "application/json" } : {},
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.error || "The request failed.");
      error.status = response.status;
      throw error;
    }
    return payload;
  } finally {
    clearTimeout(timeout);
  }
}

function selectedCrewMember() {
  return state.crew.find((member) => member.name === nameSelect.value);
}

function showAccessStep(form, title, instruction, focusSelector) {
  accessForms.forEach((item) => {
    item.hidden = item !== form;
  });
  accessTitle.textContent = title;
  accessInstruction.textContent = instruction;
  document.querySelector(focusSelector).focus();
}

function renderCrew() {
  const selectedName = nameSelect.value;
  const prompt = document.createElement("option");
  prompt.value = "";
  prompt.textContent = "Select name";
  nameSelect.replaceChildren(prompt);
  state.crew.forEach((member) => {
    const option = document.createElement("option");
    option.value = member.name;
    option.textContent = member.name;
    nameSelect.append(option);
  });
  if (state.crew.some((member) => member.name === selectedName)) {
    nameSelect.value = selectedName;
  }
}

async function loadCrew() {
  try {
    const payload = await api("/api/crew");
    state.crew = payload.crew;
    renderCrew();
  } catch (error) {
    nameError.textContent = error.message;
  }
}

function showNameStep() {
  state.member = null;
  state.claimSeedPin = "";
  loginForm.reset();
  crewPinForm.reset();
  personalPinForm.reset();
  nameError.textContent = "";
  loginError.textContent = "";
  crewPinError.textContent = "";
  personalPinError.textContent = "";
  showAccessStep(nameForm, "Boys calendar", "Choose your name.", "#name");
}

function showLoginStep() {
  loginForm.reset();
  loginError.textContent = "";
  loginUsername.value = state.member.name;
  showAccessStep(loginForm, state.member.name, "Enter your PIN.", "#login-pin");
}

function showCrewPinStep() {
  state.claimSeedPin = "";
  crewPinForm.reset();
  personalPinForm.reset();
  crewPinError.textContent = "";
  showAccessStep(
    crewPinForm,
    `Claim ${state.member.name}`,
    "Enter the crew PIN.",
    "#seed-pin",
  );
}

function showPersonalPinStep() {
  personalPinForm.reset();
  personalPinError.textContent = "";
  claimUsername.value = state.member.name;
  showAccessStep(
    personalPinForm,
    "Personal PIN",
    `Choose 4 to 8 digits for ${state.member.name}.`,
    "#new-pin",
  );
}

async function showAccess() {
  accessView.hidden = false;
  calendarView.hidden = true;
  state.member = null;
  state.claimSeedPin = "";
  state.me = "";
  state.participants = [];
  state.selected = new Set();
  state.saved = new Set();
  state.dirty = false;
  state.saving = false;
  state.conflict = null;
  state.saveError = "";
  state.generation += 1;
  nameForm.reset();
  loginForm.reset();
  crewPinForm.reset();
  personalPinForm.reset();
  showNameStep();
  await loadCrew();
}

function openCalendar(payload) {
  state.me = payload.me;
  state.participants = payload.participants;
  const mine = state.participants.find((participant) => participant.name === state.me);
  state.selected = new Set(mine?.dates || []);
  state.saved = new Set(state.selected);
  state.revision = payload.revision;
  state.dirty = false;
  state.saveError = "";
  state.conflict = null;
  state.generation += 1;
  accessView.hidden = true;
  calendarView.hidden = false;
  document.querySelector("#signed-in-label").textContent = state.me;
  render();
}

function visibleParticipants() {
  return state.participants.map((participant) =>
    participant.name === state.me ? { ...participant, dates: [...state.selected] } : participant,
  );
}

function peopleForDate(key) {
  return visibleParticipants().filter((participant) => participant.dates.includes(key));
}

function renderDay(value, outside) {
  const key = dateKey(value);
  const selectable = !outside && value >= today && value <= lastSelectableDay;
  const people = peopleForDate(key);
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.date = key;
  button.className = "calendar-day";
  button.setAttribute("role", "gridcell");
  button.setAttribute("aria-pressed", state.selected.has(key) ? "true" : "false");
  const dateName = value.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const availability = people.length
    ? ` Available: ${people.map((person) => person.name).join(", ")}.`
    : "";
  button.setAttribute("aria-label", `${dateName}.${availability}`);
  button.disabled = !selectable;
  if (outside) button.classList.add("is-outside");
  if (dateKey(value) === dateKey(today)) button.classList.add("is-today");
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
    stripe.className = `availability-stripe ${participantColorClasses[person.name]}`;
    stripes.append(stripe);
  });
  button.append(stripes);

  if (selectable) {
    button.addEventListener("click", () => {
      if (state.selected.has(key)) state.selected.delete(key);
      else state.selected.add(key);
      updateDirty();
      render();
    });
  }
  return button;
}

function renderCalendar() {
  const focused = calendarGrid.contains(document.activeElement) ? document.activeElement.dataset.date : null;
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

  if (focused) calendarGrid.querySelector(`[data-date="${focused}"]`)?.focus({ preventScroll: true });

  const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const finalMonth = new Date(lastSelectableDay.getFullYear(), lastSelectableDay.getMonth(), 1);
  previousButton.disabled = state.month <= currentMonth;
  nextButton.disabled = state.month >= finalMonth;
}

function renderLegend() {
  legend.replaceChildren();
  const participants = visibleParticipants().sort((first, second) =>
    first.name.localeCompare(second.name),
  );
  participants.forEach((participant) => {
    const item = document.createElement("span");
    item.className = "legend-item";
    const mark = document.createElement("span");
    mark.className = `legend-mark ${participantColorClasses[participant.name]}`;
    mark.setAttribute("aria-hidden", "true");
    const name = document.createElement("span");
    const identity = participant.name === state.me ? `${participant.name} (you)` : participant.name;
    const days = participant.dates.length;
    const status = participant.claimed
      ? days
        ? `${days} ${days === 1 ? "day" : "days"}`
        : "no dates"
      : "unclaimed";
    name.textContent = `${identity} · ${status}`;
    item.append(mark, name);
    legend.append(item);
  });
}

function render() {
  renderCalendar();
  renderLegend();
  const participantCount = visibleParticipants().length;
  const selectedCount = state.selected.size;
  summary.textContent = `${participantCount} boys · ${selectedCount} of your dates selected`;
  saveButton.textContent = state.saving ? "Saving…" : state.dirty ? "Save changes" : "Dates saved";
  saveButton.disabled = state.saving || !state.dirty || !!state.conflict;
  document.querySelector("#logout-button").disabled = state.saving;
  saveStatus.textContent = state.saving
    ? "Saving the submitted dates. New edits remain unsaved."
    : state.saveError || (state.dirty ? "You have unsaved changes." : "All displayed dates are saved.");
  conflictPanel.hidden = !state.conflict;
  if (state.conflict) {
    document.querySelector("#remote-dates").textContent = editableDates(mineFrom(state.conflict)).join(", ") || "No future dates";
    document.querySelector("#draft-dates").textContent = editableDates(state.selected).join(", ") || "No future dates";
  }
}

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 2600);
}

nameSelect.addEventListener("change", () => {
  nameError.textContent = "";
});

nameForm.addEventListener("submit", (event) => {
  event.preventDefault();
  nameError.textContent = "";
  const member = selectedCrewMember();
  if (!member) {
    nameError.textContent = "Choose your crew name.";
    return;
  }
  state.member = member;
  if (member.claimed) showLoginStep();
  else showCrewPinStep();
});

document.querySelectorAll(".choose-name-button").forEach((button) => {
  button.addEventListener("click", showNameStep);
});

document.querySelector("#back-to-crew-pin").addEventListener("click", showCrewPinStep);

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.member) return;
  loginError.textContent = "";
  const button = loginForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Opening…";
  const form = new FormData(loginForm);
  try {
    await api("/api/session", {
      method: "POST",
      body: JSON.stringify({ name: state.member.name, pin: form.get("pin") }),
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

crewPinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.member) return;
  crewPinError.textContent = "";
  const button = crewPinForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Checking…";
  const form = new FormData(crewPinForm);
  try {
    await api("/api/claim/check", {
      method: "POST",
      body: JSON.stringify({
        name: state.member.name,
        seed_pin: form.get("seed_pin"),
      }),
    });
    state.claimSeedPin = form.get("seed_pin");
    crewPinForm.reset();
    showPersonalPinStep();
  } catch (error) {
    crewPinError.textContent = error.message;
    if (error.message === "This name is already claimed.") {
      await loadCrew();
      showNameStep();
      nameError.textContent = error.message;
    }
  } finally {
    button.disabled = false;
    button.textContent = "Continue";
  }
});

personalPinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.member || !state.claimSeedPin) return;
  personalPinError.textContent = "";
  const button = personalPinForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Claiming…";
  const form = new FormData(personalPinForm);
  try {
    await api("/api/claim", {
      method: "POST",
      body: JSON.stringify({
        name: state.member.name,
        seed_pin: state.claimSeedPin,
        pin: form.get("pin"),
      }),
    });
    state.claimSeedPin = "";
    const payload = await api("/api/availability");
    personalPinForm.reset();
    openCalendar(payload);
  } catch (error) {
    if (error.message === "The crew PIN is not correct.") {
      showCrewPinStep();
      crewPinError.textContent = error.message;
    } else if (error.message === "This name is already claimed.") {
      await loadCrew();
      showNameStep();
      nameError.textContent = error.message;
    } else {
      personalPinError.textContent = error.message;
    }
  } finally {
    button.disabled = false;
    button.textContent = "Claim name";
  }
});

function sameDates(first, second) {
  return first.size === second.size && [...first].every((day) => second.has(day));
}

function updateDirty() {
  state.dirty = !sameDates(state.selected, state.saved);
}

function editableDates(dates) {
  return [...dates].filter((day) => day >= dateKey(new Date())).sort();
}

function mineFrom(payload) {
  return new Set(payload.participants.find((person) => person.name === state.me)?.dates || []);
}

function acceptRefresh(payload) {
  state.participants = payload.participants;
  const remote = mineFrom(payload);
  if (!state.dirty || sameDates(remote, state.selected)) {
    state.selected = remote;
    state.saved = new Set(remote);
    state.revision = payload.revision;
    state.conflict = null;
    state.saveError = "";
    updateDirty();
  } else if (payload.revision !== state.revision) {
    state.conflict = payload;
    state.saveError = "Your dates changed in another window. Compare the dates below.";
  }
  render();
}

async function refreshAvailability() {
  if (!state.me || state.saving || state.refreshing) return;
  const generation = state.generation;
  state.refreshing = true;
  try {
    const payload = await api("/api/availability");
    if (generation === state.generation && !state.saving) acceptRefresh(payload);
  } catch (error) {
    if (generation === state.generation) {
      state.saveError = error.status === 401
        ? "Your session expired. Sign in in another window, then retry. Your draft is kept here."
        : "Could not refresh other members’ dates. Your draft is kept here.";
      render();
    }
  } finally {
    state.refreshing = false;
  }
}

saveButton.addEventListener("click", async () => {
  if (state.saving || !state.dirty || state.conflict) return;
  const submitted = new Set(state.selected);
  const generation = ++state.generation;
  state.saving = true;
  state.saveError = "";
  render();
  let conflict = false;
  try {
    const payload = await api("/api/availability", {
      method: "PUT",
      body: JSON.stringify({ dates: editableDates(submitted), expected_revision: state.revision }),
    });
    if (generation !== state.generation) return;
    state.participants = payload.participants;
    state.saved = mineFrom(payload);
    state.revision = payload.revision;
    // Keep changes made while this exact snapshot was in flight.
    updateDirty();
    showToast(state.dirty ? "Submitted dates saved. Your newer edits are not saved yet." : "Your dates are saved.");
  } catch (error) {
    if (generation !== state.generation) return;
    conflict = error.status === 409;
    state.saveError = error.status === 401
      ? "Your session expired. Sign in in another window, then retry. Your draft is kept here."
      : "Save failed. Your draft is kept here. " + error.message;
  } finally {
    if (generation === state.generation) {
      state.saving = false;
      render();
      if (conflict) await refreshAvailability();
    }
  }
});

document.querySelector("#reapply-dates").addEventListener("click", () => {
  if (!state.conflict) return;
  const remote = mineFrom(state.conflict);
  const merged = new Set(remote);
  // Reapply only this window's additions and removals to the reviewed remote state.
  for (const day of state.selected) if (!state.saved.has(day)) merged.add(day);
  for (const day of state.saved) if (!state.selected.has(day)) merged.delete(day);
  state.saved = remote;
  state.selected = merged;
  state.revision = state.conflict.revision;
  state.conflict = null;
  state.saveError = "";
  updateDirty();
  render();
});

document.querySelector("#use-remote-dates").addEventListener("click", () => {
  if (!state.conflict) return;
  state.dirty = false;
  acceptRefresh(state.conflict);
});

window.addEventListener("focus", refreshAvailability);
setInterval(() => {
  if (!document.hidden) refreshAvailability();
}, 30000);
window.addEventListener("beforeunload", (event) => {
  if (state.dirty || state.saving) {
    event.preventDefault();
    event.returnValue = "";
  }
});
document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (link && link.target !== "_blank" && (state.dirty || state.saving)
      && !window.confirm("Leave without saving your changes?")) event.preventDefault();
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
  if (state.saving) return;
  if (state.dirty && !window.confirm("Exit without saving your changes?")) return;
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
  } finally {
    showAccess();
  }
});

api("/api/session")
  .then((session) => (session.authenticated ? api("/api/availability").then(openCalendar) : showAccess()))
  .catch(() => showAccess());
