(function () {
    const search = document.querySelector("#request-search");
    const list = document.querySelector(".cards");
    if (!search || !list) return;

    const cards = Array.from(list.querySelectorAll(".card"));
    const count = document.querySelector("#request-count");
    const noMatches = document.querySelector("#no-matches");

    function updateResults() {
        const words = search.value.trim().toLocaleLowerCase();
        let visible = 0;

        cards.forEach(function (card) {
            const matches = card.dataset.search.toLocaleLowerCase().includes(words);
            card.hidden = !matches;
            if (matches) visible += 1;
        });

        count.textContent = "Showing " + visible + " of " + cards.length + " requests.";
        noMatches.hidden = visible !== 0;
    }

    search.addEventListener("input", updateResults);
    updateResults();
})();
