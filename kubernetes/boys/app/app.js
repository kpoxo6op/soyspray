const state = {
  crew: [],
  member: null,
  claimSeedPin: "",
  me: "",
  participants: [],
  selected: new Set(),
  month: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  dirty: false,
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
  state.dirty = false;
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
    stripe.className = `availability-stripe ${participantColorClasses[person.name]}`;
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
  summary.textContent = `${participantCount} boys · ${selectedCount} of your dates selected`;
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
    if (error.status === 401) showAccess();
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
    showAccess();
  }
});

api("/api/session")
  .then((session) => (session.authenticated ? api("/api/availability").then(openCalendar) : showAccess()))
  .catch(() => showAccess());
