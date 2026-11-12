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

(function () {
    const button = document.querySelector("#crumple-receipt");
    const paper = document.querySelector("#request-paper");
    const message = document.querySelector("#receipt-message");
    if (!button || !paper || !message) return;

    button.addEventListener("click", function () {
        if (paper.hidden) {
            paper.hidden = false;
            paper.classList.remove("is-crumpling");
            message.hidden = true;
            button.innerHTML = 'Crumple this receipt <span aria-hidden="true">↘</span>';
            return;
        }

        paper.classList.add("is-crumpling");
        button.disabled = true;
        window.setTimeout(function () {
            paper.hidden = true;
            paper.classList.remove("is-crumpling");
            message.hidden = false;
            button.innerHTML = 'Bring receipt back <span aria-hidden="true">↖</span>';
            button.disabled = false;
        }, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 780);
    });
})();
