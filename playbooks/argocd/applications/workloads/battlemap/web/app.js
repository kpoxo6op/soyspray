(() => {
  const state = {
    data: null,
    maps: [],
    currentMapId: null,
    cy: null,
    selectedMapId: null,
    selectedNodeId: null,
    draftActive: false,
    draftPosition: null,
    tool: "select"
  };

  const $ = (id) => document.getElementById(id);

  const colorStyles = {
    blue: {bg: "#edf5ff", border: "#8ebcf2"},
    green: {bg: "#eaf8ed", border: "#94d3a2"},
    yellow: {bg: "#fff7df", border: "#e8c76f"},
    purple: {bg: "#f3edff", border: "#b69af0"},
    red: {bg: "#fff1f0", border: "#f2a7a0"},
    gray: {bg: "#f3f4f6", border: "#c9d0dc"}
  };

  function ticketByKey(key) {
    return state.data.tickets.find((ticket) => ticket.key.toUpperCase() === String(key).toUpperCase());
  }

  function currentMap() {
    return state.maps.find((map) => map.id === state.currentMapId);
  }

  function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2200);
  }

  function saveLocal() {
    localStorage.setItem("mapflow-demo-state", JSON.stringify({
      maps: state.maps,
      currentMapId: state.currentMapId
    }));
  }

  function normalizeMaps(maps) {
    return maps.map((map) => ({
      id: map.id,
      title: map.title,
      updated: map.updated,
      owner: map.owner,
      nodes: Array.isArray(map.nodes) ? map.nodes : []
    }));
  }

  function loadLocal(seed) {
    const saved = localStorage.getItem("mapflow-demo-state");
    if (!saved) {
      state.maps = normalizeMaps(structuredClone(seed.maps));
      state.currentMapId = state.maps[0].id;
      return;
    }
    try {
      const parsed = JSON.parse(saved);
      state.maps = normalizeMaps(parsed.maps?.length ? parsed.maps : structuredClone(seed.maps));
      state.currentMapId = parsed.currentMapId || state.maps[0].id;
    } catch {
      state.maps = normalizeMaps(structuredClone(seed.maps));
      state.currentMapId = state.maps[0].id;
    }
  }

  function mapElements(map) {
    const nodes = map.nodes.map((node) => {
      const ticket = ticketByKey(node.id);
      const title = ticket?.title || "Choose SPICE issue";
      const key = ticket?.key || node.id;
      const color = ticket?.color || node.color || "gray";
      const colors = colorStyles[color] || colorStyles.gray;
      return {
        group: "nodes",
        data: {
          id: node.id,
          key,
          title,
          status: ticket?.status || "Draft",
          color,
          bg: node.draft ? "#ffffff" : colors.bg,
          border: node.draft ? "#0f62fe" : colors.border,
          label: node.draft ? "New SPICE issue" : `${key}\n${title}`,
          draft: Boolean(node.draft)
        },
        position: {x: node.x, y: node.y}
      };
    });
    return nodes;
  }

  function renderMap(options = {}) {
    const map = currentMap();
    $("map-title").value = map?.title || "Untitled Map";
    $("empty-state").hidden = Boolean(map && map.nodes.length);

    if (!state.cy) {
      state.cy = cytoscape({
        container: $("cy"),
        minZoom: 0.25,
        maxZoom: 2.5,
        boxSelectionEnabled: false,
        style: [
          {
            selector: "node",
            style: {
              "shape": "round-rectangle",
              "width": 250,
              "height": 88,
              "background-color": "data(bg)",
              "border-color": "data(border)",
              "border-width": 2,
              "label": "data(label)",
              "text-wrap": "wrap",
              "text-max-width": 210,
              "font-size": 16,
              "font-family": "Inter, sans-serif",
              "color": "#111827",
              "text-valign": "center",
              "text-halign": "center",
              "overlay-padding": 8
            }
          },
          {
            selector: "node:selected",
            style: {
              "border-color": "#0f62fe",
              "border-width": 4
            }
          }
        ]
      });

      state.cy.on("tap", "node", (event) => handleNodeTap(event.target));
      state.cy.on("dragfree", "node", persistPositions);
      state.cy.on("zoom pan", updateZoomLabel);
      state.cy.on("tap", (event) => {
        if (event.target === state.cy) {
          const pos = event.position;
          if (state.tool === "pan") return;
          clearNodeSelection();
          startDraftNode(pos);
        }
      });
    }

    state.cy.elements().remove();
    state.cy.add(mapElements(map));
    if (state.selectedNodeId) {
      state.cy.getElementById(state.selectedNodeId).select();
      $("delete-node-tool").disabled = false;
    } else {
      $("delete-node-tool").disabled = true;
    }
    if (!options.keepViewport && state.cy.elements().length) state.cy.fit(undefined, 80);
    updateZoomLabel();
    updateModeBanner();
  }

  function handleNodeTap(node) {
    if (state.draftActive) return;
    selectNode(node.id());
  }

  function selectNode(id) {
    const node = state.cy.getElementById(id);
    if (!node.length) return false;
    state.selectedNodeId = id;
    state.cy.elements().unselect();
    node.select();
    $("delete-node-tool").disabled = false;
    updateModeBanner();
    showToast(`${id} selected`);
    return true;
  }

  function clearNodeSelection() {
    state.selectedNodeId = null;
    if (state.cy) state.cy.nodes().unselect();
    $("delete-node-tool").disabled = true;
    updateModeBanner();
  }

  function updateModeBanner() {
    const banner = $("mode-banner");
    if (state.draftActive) {
      banner.hidden = false;
      banner.textContent = "Type a SPICE issue number or title. Press Escape to cancel.";
    } else if (state.selectedNodeId) {
      banner.hidden = false;
      banner.textContent = `${state.selectedNodeId} selected. Use Delete Node or press Delete to remove it.`;
    } else {
      banner.hidden = true;
      banner.textContent = "";
    }
  }

  function persistPositions() {
    const map = currentMap();
    state.cy.nodes().forEach((node) => {
      const item = map.nodes.find((entry) => entry.id === node.id());
      if (item) {
        item.x = Math.round(node.position("x"));
        item.y = Math.round(node.position("y"));
      }
    });
    saveLocal();
  }

  function startDraftNode(position = {x: 0, y: 0}) {
    cancelDraftNode();
    clearNodeSelection();
    state.draftActive = true;
    state.draftPosition = position;
    $("empty-state").hidden = true;
    positionComposer(position);
    $("issue-key").value = "";
    $("issue-preview").textContent = "Enter a ticket number or title. Escape cancels.";
    $("node-composer").hidden = false;
    $("issue-key").focus();
    updateModeBanner();
  }

  function positionComposer(position) {
    const zoom = state.cy.zoom();
    const pan = state.cy.pan();
    const rendered = [position.x * zoom + pan.x, position.y * zoom + pan.y];
    const canvasRect = $("cy").getBoundingClientRect();
    const composer = $("node-composer");
    composer.style.left = `${Math.min(Math.max(rendered[0] + canvasRect.left - 125, 118), window.innerWidth - 300)}px`;
    composer.style.top = `${Math.min(Math.max(rendered[1] + canvasRect.top - 44, 92), window.innerHeight - 170)}px`;
  }

  function cancelDraftNode() {
    if (!state.draftActive) return;
    state.draftActive = false;
    state.draftPosition = null;
    $("node-composer").hidden = true;
    $("empty-state").hidden = Boolean(currentMap()?.nodes.length);
    updateModeBanner();
  }

  function normalizeIssueInput(input) {
    const raw = String(input || "").trim();
    if (!raw) return "";
    if (/^\d+$/.test(raw)) return `SPICE-${raw}`;
    const keyMatch = raw.match(/SPICE-\d+/i);
    if (keyMatch) return keyMatch[0].toUpperCase();
    const lowered = raw.toLowerCase();
    const ticket = state.data.tickets.find((item) =>
      item.title.toLowerCase().includes(lowered) || `${item.key} ${item.title}`.toLowerCase().includes(lowered)
    );
    return ticket?.key || raw.toUpperCase();
  }

  function updateIssuePreview() {
    const key = normalizeIssueInput($("issue-key").value);
    const ticket = ticketByKey(key);
    $("issue-preview").textContent = ticket ? `${ticket.key} - ${ticket.title}` : "No SPICE ticket match yet.";
  }

  function commitDraftNode(input = $("issue-key").value) {
    const key = normalizeIssueInput(input);
    const ticket = ticketByKey(key);
    if (!state.draftActive || !ticket) {
      showToast("Choose a valid SPICE issue");
      return false;
    }
    const map = currentMap();
    if (map.nodes.some((node) => node.id === ticket.key)) {
      cancelDraftNode();
      showToast(`${ticket.key} is already on the map`);
      return false;
    }
    map.nodes.push({
      id: ticket.key,
      x: Math.round(state.draftPosition.x),
      y: Math.round(state.draftPosition.y),
      color: ticket.color
    });
    state.draftActive = false;
    state.draftPosition = null;
    $("node-composer").hidden = true;
    saveLocal();
    renderMap({keepViewport: true});
    selectNode(ticket.key);
    showToast(`Added ${ticket.key}`);
    return true;
  }

  function addIssueToCurrentMap(key, position) {
    startDraftNode(position || {x: 0, y: 0});
    $("issue-key").value = key;
    updateIssuePreview();
    return commitDraftNode(key);
  }

  function deleteNode(id = state.selectedNodeId) {
    if (!id) {
      showToast("Select a node first");
      return false;
    }
    const map = currentMap();
    map.nodes = map.nodes.filter((node) => node.id !== id);
    state.selectedNodeId = null;
    saveLocal();
    renderMap({keepViewport: true});
    showToast(`Deleted ${id}`);
    return true;
  }

  function setTool(tool) {
    state.tool = tool;
    clearNodeSelection();
    document.querySelectorAll("[data-tool]").forEach((button) => {
      const active = button.dataset.tool === tool;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if (state.cy) state.cy.userPanningEnabled(tool === "pan");
    showToast(`${tool[0].toUpperCase()}${tool.slice(1)} tool`);
  }

  function updateZoomLabel() {
    if (!state.cy) return;
    $("zoom-label").textContent = `${Math.round(state.cy.zoom() * 100)}%`;
  }

  function renderOpenMapDialog() {
    const query = $("map-search").value.trim().toLowerCase();
    const maps = state.maps.filter((map) => map.title.toLowerCase().includes(query));
    $("map-list").innerHTML = maps.map((map) => `
      <button class="map-card ${map.id === state.selectedMapId ? "selected" : ""}" data-map-id="${map.id}" type="button">
        <div class="map-thumb" aria-hidden="true"></div>
        <span>
          <h3>${map.title}</h3>
          <p>${map.nodes.length} nodes · ${map.updated || "Current"}</p>
        </span>
        <span class="button secondary">Open</span>
      </button>
    `).join("");
    $("map-list").querySelectorAll("[data-map-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedMapId = button.dataset.mapId;
        renderOpenMapDialog();
      });
      button.addEventListener("dblclick", () => openSelectedMap(button.dataset.mapId));
    });
  }

  function openSelectedMap(id = state.selectedMapId) {
    if (!id) return;
    state.currentMapId = id;
    saveLocal();
    clearNodeSelection();
    cancelDraftNode();
    renderMap();
    $("open-map-dialog").close();
  }

  function createMap(title) {
    const map = {
      id: `map-${Date.now()}`,
      title: title || $("new-map-title").value || "New CFK Map",
      updated: "Current",
      owner: "You",
      nodes: []
    };
    state.maps.unshift(map);
    state.currentMapId = map.id;
    saveLocal();
    renderMap();
    showToast("Map created");
    return map.id;
  }

  function exportCytoscapeJson() {
    persistPositions();
    state.cy.data({
      format: "cytoscape.js-json",
      projectKey: state.data.project.key,
      projectName: state.data.project.name,
      mapId: currentMap().id,
      mapTitle: currentMap().title
    });
    return JSON.stringify(state.cy.json(), null, 2);
  }

  function showCode() {
    $("map-code").value = exportCytoscapeJson();
    $("code-dialog").showModal();
    saveLocal();
  }

  function wireEvents() {
    document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.tool)));
    $("add-node-tool").addEventListener("click", () => startDraftNode({x: 0, y: 0}));
    $("delete-node-tool").addEventListener("click", () => deleteNode());
    $("issue-key").addEventListener("input", updateIssuePreview);
    $("issue-key").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        commitDraftNode();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        cancelDraftNode();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.draftActive) cancelDraftNode();
      if ((event.key === "Delete" || event.key === "Backspace") && state.selectedNodeId) {
        event.preventDefault();
        deleteNode();
      }
    });
    $("open-map").addEventListener("click", () => {
      state.selectedMapId = state.currentMapId;
      renderOpenMapDialog();
      $("open-map-dialog").showModal();
    });
    $("map-search").addEventListener("input", renderOpenMapDialog);
    $("open-selected").addEventListener("click", (event) => {
      event.preventDefault();
      openSelectedMap();
    });
    $("close-map").addEventListener("click", () => $("close-map-dialog").showModal());
    $("confirm-close").addEventListener("click", (event) => {
      event.preventDefault();
      clearNodeSelection();
      $("close-map-dialog").close();
      $("open-map-dialog").showModal();
      renderOpenMapDialog();
    });
    $("create-map-action").addEventListener("click", () => $("new-map-dialog").showModal());
    $("create-map").addEventListener("click", (event) => {
      event.preventDefault();
      createMap();
      $("new-map-dialog").close();
    });
    $("save-map").addEventListener("click", showCode);
    $("map-title").addEventListener("change", () => {
      currentMap().title = $("map-title").value.trim() || "Untitled Map";
      saveLocal();
    });
    ["zoom-in", "zoom-panel-in"].forEach((id) => $(id).addEventListener("click", () => state.cy.zoom({level: state.cy.zoom() + 0.15, renderedPosition: {x: state.cy.width()/2, y: state.cy.height()/2}})));
    ["zoom-out", "zoom-panel-out"].forEach((id) => $(id).addEventListener("click", () => state.cy.zoom({level: state.cy.zoom() - 0.15, renderedPosition: {x: state.cy.width()/2, y: state.cy.height()/2}})));
    ["fit-view", "zoom-panel-fit"].forEach((id) => $(id).addEventListener("click", () => state.cy.fit(undefined, 80)));
  }

  async function init() {
    state.data = await (await fetch("/data.json")).json();
    loadLocal(state.data);
    $("issue-options").innerHTML = state.data.tickets.map((ticket) =>
      `<option value="${ticket.key}">${ticket.title}</option><option value="${ticket.key.replace("SPICE-", "")}">${ticket.key} ${ticket.title}</option>`
    ).join("");
    wireEvents();
    renderMap();
    saveLocal();

    window.mapflow = {
      state,
      createMap,
      openMap: openSelectedMap,
      addIssueToCurrentMap,
      startDraftNode,
      commitDraftNode,
      cancelDraftNode,
      selectNode,
      deleteNode,
      exportCytoscapeJson,
      resetDemo: () => {
        localStorage.removeItem("mapflow-demo-state");
        location.reload();
      }
    };
  }

  window.addEventListener("DOMContentLoaded", init);
})();
