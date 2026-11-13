(function () {
    const search = document.querySelector("#request-search");
    const skillFilter = document.querySelector("#request-skill");
    const statusFilter = document.querySelector("#request-status");
    const results = document.querySelector("#request-results");
    if (!search || !skillFilter || !statusFilter || !results) return;

    const count = document.querySelector("#request-count");
    const noMatches = document.querySelector("#no-matches");
    let requests = [];
    let loadedFromApi = false;

    function makeElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function makeCard(request) {
        const card = makeElement("li", "card testimonial-card" + (request.status === "Done" ? " done-card" : ""));
        const meta = makeElement("div", "card-meta");
        meta.append(makeElement("span", "tag", request.skill));
        meta.append(makeElement("span", "status status-" + request.status.toLowerCase(), request.status));
        card.append(meta, makeElement("span", "quote-mark", "“"));

        const heading = makeElement("h2");
        const titleLink = makeElement("a", "", request.title);
        titleLink.href = "/requests/" + request.id;
        heading.append(titleLink);
        card.append(heading);

        const description = request.description.trim();
        card.append(makeElement("p", "request-quote", description.length > 180 ? description.slice(0, 177).trimEnd() + "..." : description));

        const byline = makeElement("div", "card-byline");
        byline.append(makeElement("span", "author-mark", request.display_name.slice(0, 1).toUpperCase()));
        const author = makeElement("p", "by");
        author.append(document.createTextNode("By "));
        author.append(makeElement("strong", "", request.display_name));
        author.append(makeElement("small", "", "Request"));
        byline.append(author);

        const arrow = makeElement("a", "card-arrow", "↗");
        arrow.href = "/requests/" + request.id;
        arrow.setAttribute("aria-label", "Open request: " + request.title);
        byline.append(arrow);
        card.append(byline);
        return card;
    }

    function visibleRequests() {
        const words = search.value.trim().toLocaleLowerCase();
        const skill = skillFilter.value;
        const status = statusFilter.value;
        if (loadedFromApi) {
            return requests.filter(function (request) {
                const text = [request.title, request.description, request.display_name, request.skill, request.status]
                    .join(" ").toLocaleLowerCase();
                return text.includes(words) && (!skill || request.skill === skill) && (!status || request.status === status);
            });
        }
        return Array.from(results.querySelectorAll(".card")).filter(function (card) {
            return card.dataset.search.toLocaleLowerCase().includes(words) &&
                (!skill || card.querySelector(".tag").textContent === skill) &&
                (!status || card.querySelector(".status").textContent === status);
        });
    }

    function updateResults() {
        const visible = visibleRequests();
        if (loadedFromApi) {
            results.replaceChildren();
            if (visible.length) {
                const list = makeElement("ul", "cards");
                visible.forEach(function (request) { list.append(makeCard(request)); });
                results.append(list);
            }
        } else {
            const visibleCards = new Set(visible);
            results.querySelectorAll(".card").forEach(function (card) {
                card.hidden = !visibleCards.has(card);
            });
        }
        count.textContent = "Showing " + visible.length + " of " + (loadedFromApi ? requests.length : results.querySelectorAll(".card").length) + " requests.";
        noMatches.hidden = visible.length !== 0;
        if (loadedFromApi && requests.length === 0) {
            noMatches.textContent = "No requests yet. Be the first to ask for help!";
            noMatches.hidden = false;
        } else {
            noMatches.textContent = "No requests match your filters.";
        }
    }

    search.addEventListener("input", updateResults);
    skillFilter.addEventListener("change", updateResults);
    statusFilter.addEventListener("change", updateResults);
    updateResults();

    fetch("/api/requests")
        .then(function (response) {
            if (!response.ok) throw new Error("Could not load requests");
            return response.json();
        })
        .then(function (data) {
            requests = data.requests;
            loadedFromApi = true;
            updateResults();
        })
        .catch(function () {
            // Keep the server-rendered requests usable if the API cannot be reached.
        });
})();
