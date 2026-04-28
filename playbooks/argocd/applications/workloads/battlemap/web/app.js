(() => {
  const state = {
    data: null,
    maps: [],
    currentMapId: null,
    cy: null,
    selectedNodeId: null,
    selectedMapId: null,
    connectSourceId: null,
    tool: "select",
    dirty: false,
    recent: []
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
      currentMapId: state.currentMapId,
      recent: state.recent
    }));
    state.dirty = false;
  }

  function loadLocal(seed) {
    const saved = localStorage.getItem("mapflow-demo-state");
    if (!saved) {
      state.maps = structuredClone(seed.maps);
      state.currentMapId = state.maps[0].id;
      return;
    }
    try {
      const parsed = JSON.parse(saved);
      state.maps = parsed.maps?.length ? parsed.maps : structuredClone(seed.maps);
      state.currentMapId = parsed.currentMapId || state.maps[0].id;
      state.recent = parsed.recent || [];
    } catch {
      state.maps = structuredClone(seed.maps);
      state.currentMapId = state.maps[0].id;
    }
  }

  function markDirty() {
    state.dirty = true;
    saveLocal();
  }

  function mapElements(map) {
    const nodes = map.nodes.map((node) => {
      const ticket = ticketByKey(node.id) || {
        key: node.id,
        title: node.title || "Custom node",
        status: node.status || "Backlog",
        color: node.color || "gray",
        notes: node.notes || ""
      };
      return {
        group: "nodes",
        data: {
          id: node.id,
          key: ticket.key,
          title: ticket.title,
          status: ticket.status,
          color: ticket.color || node.color || "gray",
          notes: ticket.notes || node.notes || "",
          type: ticket.type || "Task",
          assignee: ticket.assignee || "Unassigned"
        },
        position: {x: node.x, y: node.y}
      };
    });
    const edges = map.edges.map((edge, index) => ({
      group: "edges",
      data: {id: edge.id || `${edge.source}-${edge.target}-${index}`, source: edge.source, target: edge.target}
    }));
    return [...nodes, ...edges];
  }

  function renderMap() {
    const map = currentMap();
    $("map-title").value = map?.title || "Untitled Map";
    $("empty-state").hidden = Boolean(map && map.nodes.length);

    if (!state.cy) {
      state.cy = cytoscape({
        container: $("cy"),
        minZoom: 0.25,
        maxZoom: 2.5,
        wheelSensitivity: 0.15,
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
          },
          {
            selector: "edge",
            style: {
              "width": 2,
              "line-color": "#7b8798",
              "target-arrow-color": "#7b8798",
              "target-arrow-shape": "triangle",
              "curve-style": "taxi",
              "taxi-direction": "downward",
              "taxi-turn": 44
            }
          }
        ]
      });

      state.cy.on("tap", "node", (event) => handleNodeTap(event.target));
      state.cy.on("dragfree", "node", persistPositions);
      state.cy.on("zoom pan", updateZoomLabel);
      state.cy.on("tap", (event) => {
        if (event.target === state.cy && state.tool === "select") {
          clearSelection();
        }
      });
    }

    const elements = mapElements(map).map((element) => {
      if (element.group === "nodes") {
        const colors = colorStyles[element.data.color] || colorStyles.gray;
        element.data.bg = colors.bg;
        element.data.border = colors.border;
        element.data.label = `${element.data.key}\n${element.data.title}`;
      }
      return element;
    });

    state.cy.elements().remove();
    state.cy.add(elements);
    if (elements.length) {
      state.cy.fit(undefined, 80);
    }
    updateZoomLabel();
    renderSidebars();
  }

  function handleNodeTap(node) {
    const id = node.id();
    if (state.tool === "connect") {
      if (!state.connectSourceId) {
        state.connectSourceId = id;
        showToast(`Connect from ${id}: choose target node`);
        node.select();
        return;
      }
      if (state.connectSourceId !== id) {
        connectIssues(state.connectSourceId, id);
      }
      state.connectSourceId = null;
      return;
    }
    selectNode(id);
  }

  function selectNode(id) {
    state.selectedNodeId = id;
    const node = state.cy.getElementById(id);
    state.cy.nodes().unselect();
    node.select();
    const data = node.data();
    $("add-issue-panel").hidden = true;
    $("edit-panel").hidden = false;
    $("edit-key").value = data.key;
    $("edit-title").value = data.title;
    $("edit-status").value = data.status;
    $("edit-color").value = data.color;
    $("edit-notes").value = data.notes || "";
    renderSidebars();
  }

  function clearSelection() {
    state.selectedNodeId = null;
    $("edit-panel").hidden = true;
    $("add-issue-panel").hidden = false;
    if (state.cy) state.cy.nodes().unselect();
    renderSidebars();
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
    markDirty();
  }

  function addIssueToCurrentMap(key) {
    const normalized = String(key || $("issue-key").value).trim().toUpperCase();
    const ticket = ticketByKey(normalized);
    if (!ticket) {
      showToast(`${normalized || "Issue"} is not in static SPICE data`);
      return false;
    }
    const map = currentMap();
    if (map.nodes.some((node) => node.id === ticket.key)) {
      selectNode(ticket.key);
      showToast(`${ticket.key} is already on the map`);
      return true;
    }
    const count = map.nodes.length;
    const node = {
      id: ticket.key,
      x: (count % 4) * 290 - 430,
      y: Math.floor(count / 4) * 150 - 240
    };
    map.nodes.push(node);
    state.recent = [ticket.key, ...state.recent.filter((item) => item !== ticket.key)].slice(0, 6);
    $("issue-key").value = "";
    markDirty();
    renderMap();
    selectNode(ticket.key);
    showToast(`Added ${ticket.key}`);
    return true;
  }

  function addCustomNode() {
    const map = currentMap();
    const id = `NOTE-${Date.now().toString().slice(-5)}`;
    const syntheticTicket = {
      key: id,
      title: "Planning note",
      status: "Backlog",
      type: "Note",
      assignee: "You",
      color: "gray",
      notes: "Custom planning node"
    };
    state.data.tickets.push(syntheticTicket);
    map.nodes.push({id, x: 0, y: 0});
    markDirty();
    renderMap();
    selectNode(id);
  }

  function connectIssues(source, target) {
    const map = currentMap();
    if (!map.nodes.some((node) => node.id === source) || !map.nodes.some((node) => node.id === target)) {
      showToast("Both nodes must be on the map");
      return false;
    }
    if (map.edges.some((edge) => edge.source === source && edge.target === target)) {
      showToast("Connection already exists");
      return true;
    }
    map.edges.push({source, target});
    markDirty();
    renderMap();
    showToast(`Connected ${source} to ${target}`);
    return true;
  }

  function saveNodeEdits() {
    if (!state.selectedNodeId) return;
    const oldId = state.selectedNodeId;
    const newKey = $("edit-key").value.trim().toUpperCase();
    const ticket = ticketByKey(oldId);
    if (ticket) {
      ticket.key = newKey || oldId;
      ticket.title = $("edit-title").value.trim() || ticket.title;
      ticket.status = $("edit-status").value;
      ticket.color = $("edit-color").value;
      ticket.notes = $("edit-notes").value.trim();
    }
    const map = currentMap();
    const node = map.nodes.find((entry) => entry.id === oldId);
    if (node && newKey && newKey !== oldId) {
      node.id = newKey;
      map.edges.forEach((edge) => {
        if (edge.source === oldId) edge.source = newKey;
        if (edge.target === oldId) edge.target = newKey;
      });
      state.selectedNodeId = newKey;
    }
    markDirty();
    renderMap();
    selectNode(state.selectedNodeId);
    showToast("Node saved");
  }

  function deleteSelectedNode() {
    if (!state.selectedNodeId) return;
    const id = state.selectedNodeId;
    const map = currentMap();
    map.nodes = map.nodes.filter((node) => node.id !== id);
    map.edges = map.edges.filter((edge) => edge.source !== id && edge.target !== id);
    clearSelection();
    markDirty();
    renderMap();
    showToast(`Deleted ${id}`);
  }

  function setTool(tool) {
    state.tool = tool;
    state.connectSourceId = null;
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

  function renderSidebars() {
    const statusCounts = Object.fromEntries(state.data.statuses.map((status) => [status, 0]));
    state.data.tickets.forEach((ticket) => {
      statusCounts[ticket.status] = (statusCounts[ticket.status] || 0) + 1;
    });
    $("board-summary").innerHTML = Object.entries(statusCounts).map(([status, count]) =>
      `<div class="board-pill"><strong>${count}</strong><span>${status}</span></div>`
    ).join("");

    $("recent-list").innerHTML = state.recent.length
      ? state.recent.map((key) => `<li>${key} ${ticketByKey(key)?.title || ""}</li>`).join("")
      : `<li>No recently added issues</li>`;

    const map = currentMap();
    $("node-list").innerHTML = map.nodes.length
      ? map.nodes.map((node) => {
        const ticket = ticketByKey(node.id);
        return `<li><button data-node-id="${node.id}" aria-label="Select ${node.id}">${node.id}<br><small>${ticket?.title || "Custom node"}</small></button></li>`;
      }).join("")
      : `<li>No nodes yet</li>`;
    $("node-list").querySelectorAll("button[data-node-id]").forEach((button) => {
      button.addEventListener("click", () => selectNode(button.dataset.nodeId));
    });
  }

  function renderOpenMapDialog() {
    const query = $("map-search").value.trim().toLowerCase();
    const maps = state.maps.filter((map) => map.title.toLowerCase().includes(query));
    $("map-list").innerHTML = maps.map((map) => `
      <button class="map-card ${map.id === state.selectedMapId ? "selected" : ""}" data-map-id="${map.id}" type="button">
        <div class="map-thumb" aria-hidden="true"></div>
        <span>
          <h3>${map.title}</h3>
          <p>${map.updated || "Updated now"} · ${map.owner || "You"}</p>
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
    renderMap();
    $("open-map-dialog").close();
  }

  function createMap(title) {
    const map = {
      id: `map-${Date.now()}`,
      title: title || $("new-map-title").value || "New Map",
      updated: "Current",
      owner: "You",
      nodes: [],
      edges: []
    };
    state.maps.unshift(map);
    state.currentMapId = map.id;
    saveLocal();
    clearSelection();
    renderMap();
    showToast("Map created");
    return map.id;
  }

  function wireEvents() {
    document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.tool)));
    $("add-issue").addEventListener("click", () => addIssueToCurrentMap());
    $("issue-key").addEventListener("keydown", (event) => {
      if (event.key === "Enter") addIssueToCurrentMap();
    });
    $("save-node").addEventListener("click", saveNodeEdits);
    $("delete-node").addEventListener("click", deleteSelectedNode);
    $("close-edit-panel").addEventListener("click", clearSelection);
    $("collapse-add-panel").addEventListener("click", () => $("add-issue-panel").hidden = true);
    $("add-node-tool").addEventListener("click", addCustomNode);
    $("empty-add-node").addEventListener("click", addCustomNode);
    $("empty-import-issue").addEventListener("click", () => $("issue-key").focus());
    $("empty-template").addEventListener("click", () => {
      ["SPICE-101", "SPICE-109", "SPICE-110", "SPICE-118", "SPICE-137"].forEach(addIssueToCurrentMap);
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
    $("more-menu").addEventListener("click", () => $("new-map-dialog").showModal());
    $("create-map").addEventListener("click", (event) => {
      event.preventDefault();
      createMap();
      $("new-map-dialog").close();
    });
    $("save-map").addEventListener("click", () => {
      persistPositions();
      saveLocal();
      showToast("Map saved");
    });
    $("rename-map").addEventListener("click", () => $("map-title").focus());
    $("map-title").addEventListener("change", () => {
      currentMap().title = $("map-title").value.trim() || "Untitled Map";
      markDirty();
      renderOpenMapDialog();
    });
    ["zoom-in", "zoom-panel-in"].forEach((id) => $(id).addEventListener("click", () => state.cy.zoom({level: state.cy.zoom() + 0.15, renderedPosition: {x: state.cy.width()/2, y: state.cy.height()/2}})));
    ["zoom-out", "zoom-panel-out"].forEach((id) => $(id).addEventListener("click", () => state.cy.zoom({level: state.cy.zoom() - 0.15, renderedPosition: {x: state.cy.width()/2, y: state.cy.height()/2}})));
    ["fit-view", "zoom-panel-fit"].forEach((id) => $(id).addEventListener("click", () => state.cy.fit(undefined, 80)));
  }

  async function init() {
    const response = await fetch("/data.json");
    state.data = await response.json();
    loadLocal(state.data);
    state.data.statuses.forEach((status) => {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      $("edit-status").appendChild(option);
    });
    $("issue-options").innerHTML = state.data.tickets.map((ticket) => `<option value="${ticket.key}">${ticket.title}</option>`).join("");
    wireEvents();
    renderMap();
    saveLocal();

    window.mapflow = {
      state,
      createMap,
      openMap: openSelectedMap,
      addIssueToCurrentMap,
      connectIssues,
      selectNode,
      exportState: () => JSON.parse(JSON.stringify({maps: state.maps, tickets: state.data.tickets})),
      resetDemo: () => {
        localStorage.removeItem("mapflow-demo-state");
        location.reload();
      }
    };
  }

  window.addEventListener("DOMContentLoaded", init);
})();
