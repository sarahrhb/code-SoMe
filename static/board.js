// the part where the browser does some work
(() => {
       const results = document.getElementById("request-results")
     if (!results) return
    const filters = document.getElementById("request-filters")


        const search = document.getElementById("request-search")
     const skill = document.getElementById("request-skill")
    const status = document.getElementById("request-status")
       const count = document.getElementById("request-count")
     const message = document.getElementById("request-feed-message")
      let requests = []
    // ikea for html, but the screws are included

        function el(tag, className = "", text = "") {
       const node = document.createElement(tag)
      node.className = className
         node.textContent = text
       return node
      }
     function makeCard(request) {
      const card = el("li", "card testimonial-card" + (request.status === "Done" ? " done-card" : ""))
         const meta = el("div", "card-meta")
       meta.append(el("span", "tag", request.skill))


        const statusClass = "status-" + request.status.toLowerCase().replaceAll(" ", "-")
      meta.append(el("span", "status " + statusClass, request.status))
          const quote = el("span", "quote-mark", "“")
       quote.setAttribute("aria-hidden", "true")
      card.append(meta, quote)
         const heading = el("h2")
       const link = el("a", "", request.title)
        link.href = "/requests/" + request.id
      heading.append(link)
             const excerpt = request.description.length > 180
         ? request.description.slice(0, 177).trimEnd() + "..." : request.description
      card.append(heading, el("p", "request-quote", excerpt))
         const byline = el("div", "card-byline")
       const initial = el("span", "author-mark", request.display_name.slice(0, 1).toUpperCase())
        initial.setAttribute("aria-hidden", "true")
      const author = el("p", "by")
          author.append(document.createTextNode("By "), el("strong", "", request.display_name))
       const arrow = el("a", "card-arrow")
      arrow.href = "/requests/" + request.id


         arrow.setAttribute("aria-label", "Open request: " + request.title)
       const arrowMark = el("span", "", "→")
        arrowMark.setAttribute("aria-hidden", "true")
      arrow.append(el("span", "", "Open request"), arrowMark)
          byline.append(initial, author, arrow)
       card.append(byline)
      return card
       }
    function renderRequests() {
          const query = search.value.trim().toLowerCase()
       const matching = requests.filter(request => {
        const text = [request.title, request.description, request.display_name,
             request.skill, request.status].join(" ").toLowerCase()
         return text.includes(query) && (!skill.value || request.skill === skill.value)
            && (!status.value || request.status === status.value)
      })
          const list = el("ul", "cards")


       matching.forEach(request => list.append(makeCard(request)))
      if (matching.length) {
           results.replaceChildren(list)
       } else {
          results.replaceChildren(el("p", "empty", requests.length
          ? "No requests match your filters."
              : "No requests yet. Be the first to ask for help!"))
       }
      count.textContent = matching.length + " of " + requests.length + " requests"
       }
    // asking the server for the latest thingy
      async function loadRequests() {
      try {
            const response = await fetch("/api/requests", {headers: {Accept: "application/json"}})
         if (!response.ok) throw new Error("Could not load requests")
        const data = await response.json()
           if (!Array.isArray(data) || !data.every(request => request
           && Number.isSafeInteger(request.id) && request.id > 0
            && ["title", "description", "display_name", "skill", "status"]


            .every(key => typeof request[key] === "string"))) {
              throw new Error("Invalid request data")
         }
        requests = data
           renderRequests()
         filters.hidden = false
        } catch {
            message.textContent = "Browser filtering is unavailable. You can still browse the requests below."
         message.hidden = false
      }
       }
      search.addEventListener("input", renderRequests)
    skill.addEventListener("change", renderRequests)
        status.addEventListener("change", renderRequests)
    // undo the mood i was in five seconds ago
     document.getElementById("clear-request-filters").addEventListener("click", () => {
      search.value = skill.value = status.value = ""
         renderRequests()


     })
      loadRequests()
})()
