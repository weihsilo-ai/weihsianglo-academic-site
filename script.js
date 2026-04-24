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

  function revealItems(items) {
    items.forEach(function (item, index) {
      item.classList.remove("is-visible");
      item.style.transitionDelay = Math.min(index * 35, 220) + "ms";
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
  }

  function activatePublicationTab(tabName) {
    var activePanel = null;

    document.querySelectorAll(".catalog-tab[data-pub-tab]").forEach(function (button) {
      var isActive = button.dataset.pubTab === tabName;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", String(isActive));
      button.tabIndex = isActive ? 0 : -1;
    });

    document.querySelectorAll(".publication-group[data-pub-panel]").forEach(function (panel) {
      var isActive = panel.dataset.pubPanel === tabName;
      panel.hidden = !isActive;
      if (isActive) activePanel = panel;
    });

    if (activePanel) {
      revealItems(activePanel.querySelectorAll(".paper-card"));
    }
  }

  document.querySelectorAll(".tab-button[data-tab]").forEach(function (button) {
    button.addEventListener("click", function () {
      activateTab(button.dataset.tab);
    });
  });

  document.querySelectorAll(".catalog-tab[data-pub-tab]").forEach(function (button) {
    button.addEventListener("click", function () {
      activatePublicationTab(button.dataset.pubTab);
    });

    button.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "Home" && event.key !== "End") {
        return;
      }

      var tabs = Array.prototype.slice.call(document.querySelectorAll(".catalog-tab[data-pub-tab]"));
      var index = tabs.indexOf(button);
      if (index < 0) return;

      event.preventDefault();

      var nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;

      var nextTab = tabs[nextIndex];
      activatePublicationTab(nextTab.dataset.pubTab);
      nextTab.focus();
    });
  });

  var initialTab = location.hash.replace("#", "");
  if (document.getElementById(initialTab)) {
    activateTab(initialTab);
  } else {
    revealPanel(document.querySelector(".tab-panel.is-active"));
  }

  var initialPublicationTab = document.querySelector(".catalog-tab.is-active");
  if (initialPublicationTab) {
    activatePublicationTab(initialPublicationTab.dataset.pubTab);
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
