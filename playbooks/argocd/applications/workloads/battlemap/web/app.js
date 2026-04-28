(() => {
  const state = {
    data: null,
    maps: [],
    currentMapId: null,
    cy: null,
    selectedMapId: null,
    selectedNodeId: null,
    selectedNodeIds: [],
    selectedEdgeId: null,
    connectionSourceId: null,
    draftActive: false,
    draftPosition: null,
    draftConnectFrom: null,
    suppressNextCanvasTap: false,
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
      nodes: Array.isArray(map.nodes) ? map.nodes : [],
      edges: Array.isArray(map.edges) ? map.edges : []
    }));
  }

  function loadLocal(seed) {
    state.maps = normalizeMaps(structuredClone(seed.maps));
    state.currentMapId = state.maps[0].id;
  }

  function mapElements(map) {
    const nodes = map.nodes.map((node) => {
      const ticket = ticketByKey(node.id);
      const title = ticket?.title || "Choose SPICE issue";
      const key = ticket?.key || node.id;
      const color = ticket?.color || node.color || "gray";
      const colors = colorStyles[color] || colorStyles.gray;
      const titleLines = title.replace(/\s+/g, " ").match(/.{1,26}(?:\s|$)|\S+/g) || [title];
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
          label: node.draft ? "New SPICE issue" : `${key}\n${titleLines.map((line) => line.trim()).join("\n")}`,
          draft: Boolean(node.draft)
        },
        position: {x: node.x, y: node.y}
      };
    });
    const edges = map.edges.map((edge, index) => ({
      group: "edges",
      data: {
        id: edgeId(edge, index),
        source: edge.source,
        target: edge.target
      }
    }));
    return [...nodes, ...edges];
  }

  function edgeId(edge, index = 0) {
    return edge.id || `edge-${edge.source}-${edge.target}-${index}`;
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
        boxSelectionEnabled: true,
        userPanningEnabled: false,
        style: [
          {
            selector: "node",
            style: {
              "shape": "round-rectangle",
              "width": 300,
              "height": 118,
              "background-color": "data(bg)",
              "border-color": "data(border)",
              "border-width": 2,
              "label": "data(label)",
              "text-wrap": "wrap",
              "text-max-width": 260,
              "font-size": 14,
              "font-family": "Inter, sans-serif",
              "color": "#111827",
              "text-valign": "center",
              "text-halign": "center",
              "line-height": 1.18,
              "overlay-padding": 8
            }
          },
          {
            selector: "node:selected",
            style: {
              "border-color": "#0f62fe",
              "border-width": 4
            }
          },
          {
            selector: "edge",
            style: {
              "width": 2,
              "line-color": "#a8b3c5",
              "opacity": 0.58,
              "curve-style": "straight"
            }
          },
          {
            selector: "edge:selected",
            style: {
              "line-color": "#0f62fe",
              "width": 5,
              "opacity": 1
            }
          }
        ]
      });

      state.cy.on("tap", "node", (event) => handleNodeTap(event.target));
      state.cy.on("tap", "edge", (event) => selectEdge(event.target));
      state.cy.on("boxselect select unselect", "node", syncSelectedNodes);
      state.cy.on("dragfree", "node", persistPositions);
      state.cy.on("zoom pan", () => {
        updateZoomLabel();
        positionConnectAction();
        if (state.draftActive) positionComposer(state.draftPosition);
      });
      state.cy.on("tap", (event) => {
        if (event.target === state.cy) {
          if (state.tool === "pan") return;
          if (state.suppressNextCanvasTap) {
            state.suppressNextCanvasTap = false;
            return;
          }
          if (state.draftActive) {
            commitDraftNode();
            return;
          }
          if (!state.connectionSourceId) clearSelection();
        }
      });
      state.cy.on("dbltap", (event) => {
        if (event.target === state.cy) {
          const pos = event.position;
          if (state.tool === "pan" || state.draftActive) return;
          const connectFrom = state.connectionSourceId || state.selectedNodeId;
          if (!state.connectionSourceId) clearSelection();
          startDraftNode(pos, connectFrom);
        }
      });
    }

    state.cy.elements().remove();
    state.cy.add(mapElements(map));
    if (state.selectedNodeIds.length) {
      state.selectedNodeIds.forEach((id) => state.cy.getElementById(id).select());
      $("delete-node-tool").disabled = false;
    } else {
      $("delete-node-tool").disabled = true;
    }
    if (state.selectedEdgeId) state.cy.getElementById(state.selectedEdgeId).select();
    if (!options.keepViewport && state.cy.elements().length) state.cy.fit(undefined, 80);
    updateZoomLabel();
    positionConnectAction();
    updateModeBanner();
  }

  function handleNodeTap(node) {
    if (state.draftActive) return;
    if (state.connectionSourceId) {
      connectIssues(state.connectionSourceId, node.id());
      stopConnectionMode();
      return;
    }
    selectNode(node.id());
  }

  function selectNode(id) {
    const node = state.cy.getElementById(id);
    if (!node.length) return false;
    state.selectedNodeId = id;
    state.selectedNodeIds = [id];
    state.selectedEdgeId = null;
    state.connectionSourceId = null;
    state.cy.elements().unselect();
    node.select();
    $("delete-node-tool").disabled = false;
    positionConnectAction();
    updateModeBanner();
    showToast(`${id} selected`);
    return true;
  }

  function selectEdge(edge) {
    stopConnectionMode();
    state.selectedNodeId = null;
    state.selectedNodeIds = [];
    state.selectedEdgeId = edge.id();
    state.cy.elements().unselect();
    edge.select();
    $("delete-node-tool").disabled = true;
    positionConnectAction();
    updateModeBanner();
    showToast("Connection selected");
  }

  function clearSelection() {
    state.selectedNodeId = null;
    state.selectedNodeIds = [];
    state.selectedEdgeId = null;
    state.connectionSourceId = null;
    if (state.cy) state.cy.elements().unselect();
    $("delete-node-tool").disabled = true;
    positionConnectAction();
    updateModeBanner();
  }

  function syncSelectedNodes() {
    if (!state.cy) return;
    const ids = state.cy.nodes(":selected").map((node) => node.id());
    state.selectedNodeIds = ids;
    state.selectedNodeId = ids.length === 1 ? ids[0] : null;
    if (ids.length) {
      state.selectedEdgeId = null;
      state.cy.edges().unselect();
      $("delete-node-tool").disabled = false;
    } else {
      $("delete-node-tool").disabled = true;
    }
    positionConnectAction();
    updateModeBanner();
  }

  function updateModeBanner() {
    const banner = $("mode-banner");
    if (state.draftActive) {
      banner.hidden = false;
      banner.textContent = state.draftConnectFrom
        ? `Type a SPICE issue. Click away to add it and connect from ${state.draftConnectFrom}.`
        : "Type a SPICE issue number or title. Click away to create it. Escape cancels.";
    } else if (state.connectionSourceId) {
      banner.hidden = false;
      banner.textContent = `Connecting from ${state.connectionSourceId}. Click a node, or click empty space to create and connect one.`;
    } else if (state.selectedNodeIds.length > 1) {
      banner.hidden = false;
      banner.textContent = `${state.selectedNodeIds.length} nodes selected. Use Delete Node or press Delete to remove them.`;
    } else if (state.selectedNodeId) {
      banner.hidden = false;
      banner.textContent = `${state.selectedNodeId} selected. Use Delete Node or press Delete to remove it.`;
    } else if (state.selectedEdgeId) {
      banner.hidden = false;
      banner.textContent = "Connection selected. Press Delete to remove it.";
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
    positionConnectAction();
  }

  function startDraftNode(position = {x: 0, y: 0}, connectFrom = null) {
    cancelDraftNode();
    if (!connectFrom) clearSelection();
    state.draftActive = true;
    state.draftPosition = position;
    state.draftConnectFrom = connectFrom;
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
    state.draftConnectFrom = null;
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
    const connectFrom = state.draftConnectFrom;
    state.draftActive = false;
    state.draftPosition = null;
    state.draftConnectFrom = null;
    state.connectionSourceId = null;
    $("node-composer").hidden = true;
    if (connectFrom && connectFrom !== ticket.key) {
      map.edges.push({id: `edge-${connectFrom}-${ticket.key}-${Date.now()}`, source: connectFrom, target: ticket.key});
    }
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

  function connectIssues(source, target) {
    const map = currentMap();
    if (!source || !target || source === target) return false;
    const hasSource = map.nodes.some((node) => node.id === source);
    const hasTarget = map.nodes.some((node) => node.id === target);
    if (!hasSource || !hasTarget) return false;
    const existing = map.edges.some((edge) =>
      (edge.source === source && edge.target === target) || (edge.source === target && edge.target === source)
    );
    if (existing) {
      showToast("Connection already exists");
      return true;
    }
    map.edges.push({id: `edge-${source}-${target}-${Date.now()}`, source, target});
    saveLocal();
    renderMap({keepViewport: true});
    selectEdge(state.cy.getElementById(map.edges[map.edges.length - 1].id));
    showToast(`Connected ${source} to ${target}`);
    return true;
  }

  function deleteSelectedConnection() {
    if (!state.selectedEdgeId) return false;
    const map = currentMap();
    const id = state.selectedEdgeId;
    map.edges = map.edges.filter((edge, index) => edgeId(edge, index) !== id);
    state.selectedEdgeId = null;
    saveLocal();
    renderMap({keepViewport: true});
    showToast("Connection deleted");
    return true;
  }

  function deleteNode(id = state.selectedNodeId) {
    const ids = id ? [id] : state.selectedNodeIds;
    if (!ids.length) {
      showToast("Select a node first");
      return false;
    }
    const map = currentMap();
    map.nodes = map.nodes.filter((node) => !ids.includes(node.id));
    map.edges = map.edges.filter((edge) => !ids.includes(edge.source) && !ids.includes(edge.target));
    state.selectedNodeId = null;
    state.selectedNodeIds = [];
    state.connectionSourceId = null;
    saveLocal();
    renderMap({keepViewport: true});
    showToast(ids.length === 1 ? `Deleted ${ids[0]}` : `Deleted ${ids.length} nodes`);
    return true;
  }

  function setTool(tool) {
    state.tool = tool;
    clearSelection();
    document.querySelectorAll("[data-tool]").forEach((button) => {
      const active = button.dataset.tool === tool;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if (state.cy) {
      state.cy.userPanningEnabled(tool === "pan");
      state.cy.boxSelectionEnabled(tool !== "pan");
    }
    showToast(`${tool[0].toUpperCase()}${tool.slice(1)} tool`);
  }

  function updateZoomLabel() {
    if (!state.cy) return;
    $("zoom-label").textContent = `${Math.round(state.cy.zoom() * 100)}%`;
  }

  function startConnectionMode() {
    if (!state.selectedNodeId) return false;
    state.connectionSourceId = state.selectedNodeId;
    state.selectedEdgeId = null;
    if (state.cy) state.cy.edges().unselect();
    positionConnectAction();
    updateModeBanner();
    showToast(`Connect from ${state.connectionSourceId}`);
    return true;
  }

  function stopConnectionMode() {
    state.connectionSourceId = null;
    positionConnectAction();
    updateModeBanner();
  }

  function positionConnectAction() {
    const button = $("connect-node-action");
    if (!button || !state.cy || !state.selectedNodeId || state.draftActive) {
      if (button) button.hidden = true;
      return;
    }
    const node = state.cy.getElementById(state.selectedNodeId);
    if (!node.length) {
      button.hidden = true;
      return;
    }
    const rendered = node.renderedPosition();
    const canvasRect = $("cy").getBoundingClientRect();
    button.style.left = `${Math.round(canvasRect.left + rendered.x + 104)}px`;
    button.style.top = `${Math.round(canvasRect.top + rendered.y - 68)}px`;
    button.classList.toggle("active", state.connectionSourceId === state.selectedNodeId);
    button.hidden = false;
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
    clearSelection();
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
      nodes: [],
      edges: []
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

  function handleDraftClickAway(event) {
    if (!state.draftActive) return;
    if ($("node-composer").contains(event.target)) return;
    if (!$("issue-key").value.trim()) return;
    if (commitDraftNode() && $("cy").contains(event.target)) {
      state.suppressNextCanvasTap = true;
    }
  }

  function wireEvents() {
    document.addEventListener("pointerdown", handleDraftClickAway, true);
    document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.tool)));
    $("add-node-tool").addEventListener("click", () => startDraftNode({x: 0, y: 0}));
    $("delete-node-tool").addEventListener("click", () => deleteNode());
    $("connect-node-action").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      startConnectionMode();
    });
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
    $("issue-key").addEventListener("blur", () => {
      if (state.draftActive && $("issue-key").value.trim() && commitDraftNode()) {
        state.suppressNextCanvasTap = true;
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.draftActive) cancelDraftNode();
      if (event.key === "Escape" && state.connectionSourceId) stopConnectionMode();
      if ((event.key === "Delete" || event.key === "Backspace") && state.selectedEdgeId) {
        event.preventDefault();
        deleteSelectedConnection();
      }
      if ((event.key === "Delete" || event.key === "Backspace") && state.selectedNodeIds.length) {
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
      clearSelection();
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
      `<option value="${ticket.key}" label="${ticket.title}"></option>`
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
      startConnectionMode,
      connectIssues,
      deleteSelectedConnection,
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
