(function () {
    const filters = document.querySelector("#request-filters");
    const search = document.querySelector("#request-search");
    const skillFilter = document.querySelector("#request-skill");
    const statusFilter = document.querySelector("#request-status");
    const results = document.querySelector("#request-results");
    if (!filters || !search || !skillFilter || !statusFilter || !results) {
      return;
    }

    const count = document.querySelector("#request-count");
    const feedMessage = document.querySelector("#request-feed-message");
    const boardEmpty = document.querySelector("#board-empty");
    const noMatches = document.querySelector("#no-matches");
    const clearButton = document.querySelector("#clear-request-filters");
    let requests = [];
    let loadedFromApi = false;

    filters.hidden = false;

    function makeElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function makeCard(request) {
        const id = Number(request.id);
        const title = String(request.title || "");
        const description = String(request.description || "").trim();
        const displayName = String(request.display_name || "");
        const skill = String(request.skill || "Other");
        let status = "Open";
        if (request.status === "Done") {
            status = "Done";
        }
        const card = makeElement("li", "card testimonial-card" + (status === "Done" ? " done-card" : ""));
        const meta = makeElement("div", "card-meta");
        meta.append(makeElement("span", "tag", skill));
        meta.append(makeElement("span", "status status-" + status.toLowerCase(), status));
        card.append(meta, makeElement("span", "quote-mark", "“"));

        const heading = makeElement("h2");
        const titleLink = makeElement("a", "", title);
        titleLink.href = "/requests/" + id;
        heading.append(titleLink);
        card.append(heading);

        let excerpt = description;
        if (description.length > 180) {
          excerpt = description.slice(0, 177).trimEnd() + "...";
        }
        card.append(makeElement("p", "request-quote", excerpt));

        const byline = makeElement("div", "card-byline");
        byline.append(makeElement("span", "author-mark", displayName.slice(0, 1).toUpperCase()));
        const author = makeElement("p", "by");
        author.append(document.createTextNode("By "));
        author.append(makeElement("strong", "", displayName));
        byline.append(author);

        const arrow = makeElement("a", "card-arrow");
        arrow.href = "/requests/" + id;
        arrow.setAttribute("aria-label", "Open request: " + title);
        arrow.append(makeElement("span", "", "Open request"));
        const arrowMark = makeElement("span", "", "→");
        arrowMark.setAttribute("aria-hidden", "true");
        arrow.append(arrowMark);
        byline.append(arrow);
        card.append(byline);
        return card;
    }

    function matches(request, words, skill, status) {
        const text = [request.title, request.description, request.display_name, request.skill, request.status]
            .join(" ").toLocaleLowerCase();
        return text.includes(words) && (!skill || request.skill === skill) && (!status || request.status === status);
    }

    function updateResults() {
        const words = search.value.trim().toLocaleLowerCase();
        const skill = skillFilter.value;
        const status = statusFilter.value;

        if (loadedFromApi) {
            const visible = requests.filter(function (request) { return matches(request, words, skill, status); });
            results.replaceChildren();
            boardEmpty.hidden = requests.length !== 0;
            noMatches.hidden = requests.length === 0 || visible.length !== 0;
            if (visible.length) {
                const list = makeElement("ul", "cards");
                for (const request of visible) {
                    const card = makeCard(request);
                    list.append(card);
                }
                results.append(list);
            }
            count.textContent = requests.length ? "Showing " + visible.length + " of " + requests.length + " requests." : "";
            return;
        }

        const cards = Array.from(results.querySelectorAll(".card"));
        let visible = 0;
        cards.forEach(function (card) {
            const cardSkill = card.querySelector(".tag").textContent;
            const cardStatus = card.querySelector(".status").textContent;
            const match = card.dataset.search.toLocaleLowerCase().includes(words) &&
                (!skill || cardSkill === skill) && (!status || cardStatus === status);
            card.hidden = !match;
            if (match) visible += 1;
        });
        count.textContent = cards.length ? "Showing " + visible + " of " + cards.length + " requests." : "";
        boardEmpty.hidden = true;
        noMatches.hidden = cards.length === 0 || visible !== 0;
    }

    function setFeedMessage(message, withRetry) {
        feedMessage.replaceChildren();
        feedMessage.hidden = !message;
        if (!message) return;
        feedMessage.append(document.createTextNode(message));
        if (withRetry) {
            const retry = makeElement("button", "retry-button", "Try again");
            retry.type = "button";
            retry.addEventListener("click", loadRequests);
            feedMessage.append(document.createTextNode(" "), retry);
        }
    }

    function loadRequests() {
        results.setAttribute("aria-busy", "true");
        setFeedMessage("Checking for the latest requests…", false);
        fetch("/api/requests", { headers: { Accept: "application/json" }, cache: "no-store" })
            .then(function (response) {
                if (!response.ok) throw new Error("Request list unavailable");
                return response.json();
            })
            .then(function (data) {
                if (!data || !Array.isArray(data.requests)) throw new Error("Request list unavailable");
                requests = data.requests.filter(function (request) {
                    return Number.isSafeInteger(Number(request.id)) &&
                        typeof request.title === "string" && typeof request.description === "string" &&
                        typeof request.display_name === "string";
                });
                loadedFromApi = true;
                results.setAttribute("aria-busy", "false");
                setFeedMessage("", false);
                updateResults();
            })
            .catch(function () {
                results.setAttribute("aria-busy", "false");
                setFeedMessage("Couldn’t refresh requests. The list already shown is still available.", true);
                updateResults();
            });
    }

    search.addEventListener("input", updateResults);
    skillFilter.addEventListener("change", updateResults);
    statusFilter.addEventListener("change", updateResults);
    clearButton.addEventListener("click", function () {
        search.value = "";
        skillFilter.value = "";
        statusFilter.value = "";
        search.focus();
        updateResults();
    });
    updateResults();
    loadRequests();
})();
