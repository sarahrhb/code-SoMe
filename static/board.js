// the part where the browser does some work
// box = results, tools = filters, r = one request
(() => {
       const box = document.getElementById("request-results")
     if (!box) return
    const tools = document.getElementById("request-filters")


        const search = document.getElementById("request-search")
     const skill = document.getElementById("request-skill")
    const status = document.getElementById("request-status")
       const count = document.getElementById("request-count")
     const msg = document.getElementById("request-feed-message")
      let requests = []

        function el(tag, cls = "", t = "") {
       const e = document.createElement(tag)
      e.className = cls
         e.textContent = t
       return e
      }
    // make one request card
     function card(r) {
      const item = el("li", "card" + (r.status === "Done" ? " done-card" : ""))
         const tags = el("div", "card-top")
       tags.append(el("span", "tag", r.skill))


        const sc = "status-" + r.status.toLowerCase().replaceAll(" ", "-")
      tags.append(el("span", "status " + sc, r.status))
          const q = el("span", "quote-mark", "“")
       q.setAttribute("aria-hidden", "true")
      item.append(tags, q)
         const h = el("h2")
       const a = el("a", "", r.title)
        a.href = "/requests/" + r.id
      h.append(a)
             const desc = r.description.length > 180
         ? r.description.slice(0, 177).trimEnd() + "..." : r.description
      item.append(h, el("p", "card-text", desc))
         const by = el("div", "card-bottom")
       const first = el("span", "initial", r.display_name.slice(0, 1).toUpperCase())
        first.setAttribute("aria-hidden", "true")
      const name = el("p", "by")
          name.append(document.createTextNode("By "), el("strong", "", r.display_name))
       const open = el("a", "card-link")
      open.href = "/requests/" + r.id


         open.setAttribute("aria-label", "Open request: " + r.title)
       const mark = el("span", "", "→")
        mark.setAttribute("aria-hidden", "true")
      open.append(el("span", "", "Open request"), mark)
          by.append(first, name, open)
       item.append(by)
      return item
       }
    // filter the list and show the matching cards
    function finishRequests() {
          const word = search.value.trim().toLowerCase()
       const found = requests.filter(r => {
        const t = [r.title, r.description, r.display_name,
             r.skill, r.status].join(" ").toLowerCase()
         return t.includes(word) && (!skill.value || r.skill === skill.value)
            && (!status.value || r.status === status.value)
      })
          const list = el("ul", "cards")


       found.forEach(r => list.append(card(r)))
      if (found.length) {
           box.replaceChildren(list)
       } else {
          box.replaceChildren(el("p", "empty", requests.length
          ? "No requests match your filters."
              : "No requests yet. Be the first to ask for help!"))
       }
      count.textContent = found.length + " of " + requests.length + " requests"
       }
    // asking the server for the latest thingy
    // load the json from the server
      async function getRequests() {
      try {
            const res = await fetch("/api/requests", {headers: {Accept: "application/json"}})
         if (!res.ok) throw new Error("Could not load requests")
        const data = await res.json()
           if (!Array.isArray(data) || !data.every(r => r
           && Number.isSafeInteger(r.id) && r.id > 0
            && ["title", "description", "display_name", "skill", "status"]


            .every(key => typeof r[key] === "string"))) {
              throw new Error("Invalid request data")
         }
        requests = data
           finishRequests()
         tools.hidden = false
        } catch {
            msg.textContent = "Browser filtering is unavailable. You can still browse the requests below."
         msg.hidden = false
      }
       }
    // update the cards when a filter changes
      search.addEventListener("input", finishRequests)
    skill.addEventListener("change", finishRequests)
        status.addEventListener("change", finishRequests)
    // undo the mood i was in five seconds ago
     document.getElementById("clear-request-filters").addEventListener("click", () => {
      search.value = skill.value = status.value = ""
         finishRequests()


     })
      getRequests()
})()
