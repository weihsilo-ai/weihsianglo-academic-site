(function () {
  document.documentElement.classList.add("motion-ready");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function animateCounts(container) {
    if (reduceMotion) return;

    container.querySelectorAll(".stat-card strong").forEach(function (node) {
      var target = Number(node.dataset.target || node.textContent);
      if (!Number.isFinite(target)) return;

      node.dataset.target = String(target);
      node.textContent = "0";

      var start = null;
      function step(timestamp) {
        if (!start) start = timestamp;
        var progress = Math.min((timestamp - start) / 780, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        node.textContent = String(Math.round(target * eased));
        if (progress < 1) {
          window.requestAnimationFrame(step);
        }
      }

      window.requestAnimationFrame(step);
    });
  }

  function revealPanel(panel) {
    if (!panel) return;

    var items = panel.querySelectorAll(
      ".dashboard-card, .theme-chip, .research-focus-card, .timeline article, .paper-card, .education-card, .award-tile"
    );

    items.forEach(function (item, index) {
      item.classList.remove("is-visible");
      item.style.transitionDelay = Math.min(index * 35, 260) + "ms";
    });

    window.requestAnimationFrame(function () {
      items.forEach(function (item) {
        item.classList.add("is-visible");
      });
    });

    window.setTimeout(function () {
      items.forEach(function (item) {
        item.style.transitionDelay = "";
      });
    }, 650);

    animateCounts(panel);
  }

  function activateTab(tabName) {
    var activePanel = null;

    document.querySelectorAll(".tab-button[data-tab]").forEach(function (button) {
      var isActive = button.dataset.tab === tabName;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", String(isActive));
    });

    document.querySelectorAll(".tab-panel").forEach(function (panel) {
      var isActive = panel.id === tabName;
      panel.classList.toggle("is-active", isActive);
      panel.hidden = !isActive;
      if (isActive) activePanel = panel;
    });

    if (history.replaceState) {
      history.replaceState(null, "", "#" + tabName);
    }

    if (activePanel) {
      revealPanel(activePanel);
    }
  }

  document.querySelectorAll(".tab-button[data-tab]").forEach(function (button) {
    button.addEventListener("click", function () {
      activateTab(button.dataset.tab);
    });
  });

  var initialTab = location.hash.replace("#", "");
  if (document.getElementById(initialTab)) {
    activateTab(initialTab);
  } else {
    revealPanel(document.querySelector(".tab-panel.is-active"));
  }

  function togglePaper(card) {
    var expanded = !card.classList.contains("is-expanded");
    card.classList.toggle("is-expanded", expanded);
    card.setAttribute("aria-expanded", String(expanded));
    var button = card.querySelector(".paper-toggle");
    if (button) {
      button.setAttribute("aria-label", expanded ? "Collapse paper" : "Expand paper");
    }
  }

  document.querySelectorAll(".paper-card").forEach(function (card) {
    card.addEventListener("click", function (event) {
      if (event.target.closest("a")) return;
      togglePaper(card);
    });

    card.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      if (event.target.closest("a")) return;
      event.preventDefault();
      togglePaper(card);
    });
  });
})();
