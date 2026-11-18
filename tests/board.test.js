const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const source = readFileSync(join(__dirname, "../static/board.js"), "utf8");

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.value = "";
        this.hidden = true;
        this.listeners = {};
    }
    set textContent(value) { this.text = String(value); this.children = []; }
    get textContent() { return (this.text || "") + this.children.map(child => child.textContent).join(""); }
    set innerHTML(value) { throw new Error("Request content must not use innerHTML"); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.text = ""; this.children = children; }
    addEventListener(type, callback) { this.listeners[type] = callback; }
    setAttribute(name, value) { this[name] = value; }
}

async function board(response) {
    const elements = {};
    for (const id of ["request-results", "request-filters", "request-search", "request-skill",
        "request-status", "request-count", "request-feed-message", "clear-request-filters"]) {
        elements[id] = new Element("div");
    }
    elements["request-results"].textContent = "Server-rendered fallback";
    vm.runInNewContext(source, {
        document: {
            getElementById: id => elements[id],
            createElement: tag => new Element(tag),
            createTextNode: text => { const node = new Element("text"); node.textContent = text; return node; }
        },
        fetch: async (url) => { assert.equal(url, "/api/requests"); return response; }
    });
    await new Promise(resolve => setImmediate(resolve));
    return elements;
}

const rows = [
    {id: 2, title: '<img src=x onerror="alert(1)">', description: "Berlin shoot", display_name: "Sarah", skill: "Filming", status: "In progress"},
    {id: 1, title: "Logo", description: "New design", display_name: "Max", skill: "Design", status: "Done"}
];

test("loads cards as text and combines search, skill and status filters", async () => {
    const e = await board({ok: true, json: async () => rows});
    assert.equal(e["request-filters"].hidden, false);
    assert.equal(e["request-count"].textContent, "2 of 2 requests");
    assert.ok(e["request-results"].textContent.includes(rows[0].title));
    const card = e["request-results"].children[0].children[0];
    assert.equal(card.children[2].children[0].href, "/requests/2");
    e["request-search"].value = " BERLIN ";
    e["request-search"].listeners.input();
    assert.equal(e["request-count"].textContent, "1 of 2 requests");
    e["request-status"].value = "In progress";
    e["request-status"].listeners.change();
    assert.equal(e["request-count"].textContent, "1 of 2 requests");
    e["request-skill"].value = "Design";
    e["request-skill"].listeners.change();
    assert.equal(e["request-count"].textContent, "0 of 2 requests");
    assert.match(e["request-results"].textContent, /No requests match/);
    e["clear-request-filters"].listeners.click();
    assert.equal(e["request-count"].textContent, "2 of 2 requests");
});

test("empty feed has a useful empty state", async () => {
    const e = await board({ok: true, json: async () => []});
    assert.match(e["request-results"].textContent, /No requests yet/);
    assert.equal(e["request-count"].textContent, "0 of 0 requests");
});

test("failed or malformed feeds preserve server-rendered requests", async () => {
    for (const response of [
        {ok: false},
        {ok: true, json: async () => ({error: "unavailable"})},
        {ok: true, json: async () => [{...rows[0], id: "javascript:alert(1)"}]},
        {ok: true, json: async () => { throw new Error("Invalid JSON"); }}
    ]) {
        const e = await board(response);
        assert.equal(e["request-results"].textContent, "Server-rendered fallback");
        assert.equal(e["request-filters"].hidden, true);
        assert.equal(e["request-feed-message"].hidden, false);
    }
});
