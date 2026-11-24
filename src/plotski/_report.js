(() => {
    const root = document.currentScript.parentElement;
    const backend = root.dataset.backend;
    const tabs = Array.from(root.querySelectorAll("[role=tab]"));
    const panels = tabs.map(tab => document.getElementById(tab.getAttribute("aria-controls")));
    const axes = new Map();
    const selections = new Map();
    const bokehSources = new Map();

    function sameRange(left, right) {
        return left?.length === 2 && right?.length === 2 && left[0] === right[0] && left[1] === right[1];
    }

    async function applyRange(axis, range) {
        axis.pending = range;
        if (axis.writing) return;
        axis.writing = true;
        try {
            while (axis.pending) {
                const requested = axis.pending;
                axis.pending = null;
                if (!sameRange(axis.read(), requested)) await axis.write(requested);
            }
        } finally {
            axis.writing = false;
        }
    }

    function connectAxis(key, axis) {
        const initial = axis.read();
        if (!axes.has(key)) axes.set(key, {range: initial, endpoints: []});
        const group = axes.get(key);
        group.endpoints.push(axis);
        if (group.range) void applyRange(axis, group.range);
        else group.range = initial;
        axis.watch(reset => {
            if (axis.writing) return;
            const range = reset && initial ? initial : axis.read();
            if (!range) return;
            group.range = range;
            for (const peer of group.endpoints) void applyRange(peer, range);
        });
    }

    function selection(group) {
        if (!selections.has(group)) selections.set(group, {id: null, rows: [], plots: []});
        return selections.get(group);
    }

    function select(group, id) {
        if (id === undefined) return;
        const state = selection(group);
        state.id = state.id === id ? null : id;
        for (const row of state.rows) {
            const active = row.dataset.selectionId === state.id;
            row.classList.toggle("plotski-selected", active);
            row.querySelector("button").setAttribute("aria-pressed", String(active));
        }
        // Apply after native click handlers finish updating their local selections.
        queueMicrotask(() => {
            for (const plot of state.plots) plot(state.id);
        });
    }

    root.querySelectorAll("table[data-selection-group]").forEach(table => {
        const group = table.dataset.selectionGroup;
        for (const row of table.querySelectorAll("[data-selection-id]")) selection(group).rows.push(row);
        table.addEventListener("click", event => {
            const row = event.target.closest("[data-selection-id]");
            if (row) select(group, row.dataset.selectionId);
        });
    });

    function matching(ids, id) {
        return id === null ? [] : Array.from(ids.keys()).filter(index => ids[index] === id);
    }

    const bokehClicks = new Map();
    root.addEventListener("plotski-bokeh-select", event => {
        const binding = bokehSources.get(event.detail.source);
        if (!binding || bokehClicks.has(binding.group)) return;
        if (!bokehClicks.size) {
            queueMicrotask(() => {
                for (const [group, id] of bokehClicks) select(group, id);
                bokehClicks.clear();
            });
        }
        bokehClicks.set(binding.group, binding.ids[event.detail.index]);
    });

    async function mountBokeh(target, payload) {
        await Bokeh.embed.embed_item(payload.plot, target.id);
        const doc = Bokeh.documents.find(item => item.get_model_by_id(payload.plot.root_id));
        for (const [name, key] of Object.entries(payload.axes)) {
            const range = doc.get_model_by_id(name);
            const read = () => Number.isFinite(range.start) && Number.isFinite(range.end) ? [range.start, range.end] : null;
            connectAxis(key, {
                read,
                write: ([start, end]) => range.setv({start, end}),
                watch(update) {
                    let scheduled = false;
                    function changed() {
                        if (scheduled) return;
                        scheduled = true;
                        queueMicrotask(() => {
                            scheduled = false;
                            if (!sameRange(read(), axes.get(key).range)) update(false);
                        });
                    }
                    range.properties.start.change.connect(changed);
                    range.properties.end.change.connect(changed);
                },
            });
        }
        for (const [name, group] of Object.entries(payload.selection)) {
            const source = doc.get_model_by_id(name);
            const ids = source.data._plotski_id;
            bokehSources.set(name, {group, ids});
            const state = selection(group);
            const apply = id => { source.selected.indices = matching(ids, id); };
            state.plots.push(apply);
            apply(state.id);
        }
    }

    async function mountPlotly(target, payload) {
        const {data, layout, config} = payload.plot;
        await Plotly.newPlot(target, data, layout, config);
        const linked = new Map();
        for (const [name, key] of Object.entries(payload.axes)) {
            if (!linked.has(key)) linked.set(key, []);
            linked.get(key).push(name);
        }
        for (const [key, names] of linked) {
            // Plotly matches the other local axes to this first axis.
            const name = names[0];
            const read = () => Array.from(target._fullLayout[name].range);
            connectAxis(key, {
                read,
                write: range => Plotly.relayout(target, {[name + ".autorange"]: false, [name + ".range"]: range}),
                watch(update) {
                    target.on("plotly_relayout", event => {
                        if (names.some(axis => event[axis + ".autorange"])) update(true);
                        else if (names.some(axis => [".range", ".range[0]", ".range[1]"].some(prop => axis + prop in event))) {
                            update(false);
                        }
                    });
                },
            });
        }
        target.on("plotly_click", event => {
            const point = event.points.find(point => payload.selection[point.curveNumber] !== undefined);
            if (point) select(payload.selection[point.curveNumber], point.data.ids[point.pointNumber]);
        });
        for (const [index, group] of Object.entries(payload.selection)) {
            const ids = target.data[index].ids;
            const state = selection(group);
            const apply = id => Plotly.restyle(target, "selectedpoints", [id === null ? null : matching(ids, id)], [Number(index)]);
            state.plots.push(apply);
            if (state.id !== null) await apply(state.id);
        }
    }

    const mounted = new WeakMap();
    function mount(grid) {
        if (mounted.has(grid)) return mounted.get(grid);
        const [target, data] = grid.children;
        const payload = JSON.parse(data.textContent);
        const render = backend === "bokeh" ? mountBokeh : mountPlotly;
        const result = render(target, payload).then(() => {
            grid.dataset.plotskiReady = "true";
        }).catch(error => {
            target.textContent = "This plot could not be rendered.";
            console.error(error);
        });
        mounted.set(grid, result);
        return result;
    }

    async function selectTab(index, focus) {
        tabs.forEach((tab, i) => {
            tab.setAttribute("aria-selected", String(i === index));
            tab.tabIndex = i === index ? 0 : -1;
            panels[i].hidden = i !== index;
        });
        if (focus) tabs[index].focus();
        const panel = panels[index];
        const grids = Array.from(panel.querySelectorAll(".plotski-grid"));
        await Promise.all(grids.map(mount));
        if (backend === "plotly" && !panel.hidden) {
            for (const grid of grids) {
                if (grid.dataset.plotskiReady) void Plotly.Plots.resize(grid.firstElementChild);
            }
        }
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => void selectTab(index, false));
        tab.addEventListener("keydown", event => {
            const next = {
                ArrowRight: (index + 1) % tabs.length,
                ArrowLeft: (index + tabs.length - 1) % tabs.length,
                Home: 0,
                End: tabs.length - 1,
            }[event.key];
            if (next === undefined) return;
            event.preventDefault();
            void selectTab(next, true);
        });
    });

    const lazy = root.dataset.lazyTabs === "true";
    root.querySelectorAll(".plotski-grid").forEach(grid => {
        if (!lazy || !grid.closest("[role=tabpanel][hidden]")) void mount(grid);
    });
})();
