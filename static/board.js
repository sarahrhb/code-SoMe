(() => {
    const results = document.getElementById("request-results");
    if (!results) return;

    const filters = document.getElementById("request-filters");
    const search = document.getElementById("request-search");
    const skill = document.getElementById("request-skill");
    const status = document.getElementById("request-status");
    const count = document.getElementById("request-count");
    const message = document.getElementById("request-feed-message");
    let requests = [];

    function makeElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function makeCard(request) {
        const card = makeElement("li", "card");
        card.append(makeElement("span", "tag", request.skill));
        card.append(document.createTextNode(" "));
        const statusClass = "status-" + request.status.toLowerCase().replaceAll(" ", "-");
        card.append(makeElement("span", "status " + statusClass, request.status));
        const heading = makeElement("h2");
        const link = makeElement("a", "", request.title);
        link.href = "/requests/" + request.id;
        heading.append(link);
        card.append(heading, makeElement("p", "by", "by " + request.display_name));
        return card;
    }

    function renderRequests() {
        const query = search.value.trim().toLowerCase();
        const matching = requests.filter(request => {
            const text = [request.title, request.description, request.display_name,
                request.skill, request.status].join(" ").toLowerCase();
            return text.includes(query) && (!skill.value || request.skill === skill.value)
                && (!status.value || request.status === status.value);
        });
        const list = makeElement("ul", "cards");
        matching.forEach(request => list.append(makeCard(request)));
        if (matching.length) {
            results.replaceChildren(list);
        } else {
            results.replaceChildren(makeElement("p", "empty", requests.length
                ? "No requests match your filters."
                : "No requests yet. Be the first to ask for help!"));
        }
        count.textContent = matching.length + " of " + requests.length + " requests";
    }

    async function loadRequests() {
        try {
            const response = await fetch("/api/requests", {headers: {Accept: "application/json"}});
            if (!response.ok) throw new Error("Could not load requests");
            const data = await response.json();
            if (!Array.isArray(data) || !data.every(request => request
                && Number.isSafeInteger(request.id) && request.id > 0
                && ["title", "description", "display_name", "skill", "status"]
                    .every(key => typeof request[key] === "string"))) {
                throw new Error("Invalid request data");
            }
            requests = data;
            renderRequests();
            filters.hidden = false;
        } catch (error) {
            message.textContent = "Browser filtering is unavailable. You can still browse the requests below.";
            message.hidden = false;
        }
    }

    search.addEventListener("input", renderRequests);
    skill.addEventListener("change", renderRequests);
    status.addEventListener("change", renderRequests);
    document.getElementById("clear-request-filters").addEventListener("click", () => {
        search.value = skill.value = status.value = "";
        renderRequests();
    });
    loadRequests();
})();
