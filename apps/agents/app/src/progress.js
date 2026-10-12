import { defaultState, readState, storageKey } from "./workshop-data.js";

export function createProgress(lessonIds) {
    let state = defaultState();
    let storageAvailable = true;
    try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            try { state = readState(JSON.parse(saved), lessonIds); }
            catch { /* A corrupt saved object does not prevent reading. */ }
        }
    } catch { storageAvailable = false; }
    function refresh() {
        try {
            const raw = localStorage.getItem(storageKey);
            if (raw) {
                try { state = readState(JSON.parse(raw), lessonIds); }
                catch { /* A corrupt object does not stop the visit's working state. */ }
            } else state = defaultState();
            storageAvailable = true;
            return true;
        } catch { storageAvailable = false; return false; }
    }
    function save(change) {
        const readable = refresh();
        change?.(state);
        if (!readable) return;
        try { localStorage.setItem(storageKey, JSON.stringify(state)); storageAvailable = true; }
        catch { storageAvailable = false; }
    }
    return {
        get state() { return state; },
        get storageAvailable() { return storageAvailable; },
        set(key, value) { save(current => current[key] = value); },
        finish(id, on) {
            save(current => {
                current.completed = current.completed.filter(value => value !== id);
                if (on) current.completed.push(id);
            });
        },
        note(key, text) { save(current => current.adoption[key] = text); },
        import(value) {
            if (value?.version !== 1) throw new Error("Choose a version 1 progress export.");
            const imported = readState(value.state, lessonIds);
            state = imported;
            try { localStorage.setItem(storageKey, JSON.stringify(imported)); storageAvailable = true; }
            catch { storageAvailable = false; }
        },
        export() { refresh(); return JSON.stringify({ version: 1, state }, null, 2); },
        reset() {
            state = defaultState();
            try { localStorage.removeItem(storageKey); } catch { storageAvailable = false; }
        },
    };
}

export function downloadText(name, text, type = "text/plain") {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
