(function () {
  document.documentElement.classList.add("motion-ready");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

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
      ".dashboard-card, .theme-chip, .timeline article, .paper-card, .education-card, .award-tile"
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

  function activatePublicationTab(tabName) {
    var activePanels = [];

    document.querySelectorAll(".catalog-tab[data-pub-tab]").forEach(function (button) {
      var isActive = button.dataset.pubTab === tabName;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", String(isActive));
      button.tabIndex = isActive ? 0 : -1;
    });

    document.querySelectorAll(".publication-group[data-pub-panel]").forEach(function (panel) {
      var isActive = tabName === "all" || panel.dataset.pubPanel === tabName;
      panel.hidden = !isActive;
      if (isActive) activePanels.push(panel);
    });

    if (activePanels.length) {
      var items = [];
      activePanels.forEach(function (panel) {
        items = items.concat(Array.prototype.slice.call(panel.querySelectorAll(".paper-card")));
      });
      revealItems(items);
    }
  }

  function renderTags(tags) {
    return (tags || [])
      .map(function (tag) {
        var label = typeof tag === "string" ? tag : tag && tag.label;
        if (!label) return "";
        var tone = tag && tag.tone ? " tag-" + escapeHtml(tag.tone) : "";
        return '<span class="tag' + tone + '">' + escapeHtml(label) + "</span>";
      })
      .join("");
  }

  function renderLinks(links) {
    return (links || [])
      .map(function (link) {
        if (!link || !link.label || !link.href) return "";
        return '<a href="' + escapeHtml(link.href) + '">' + escapeHtml(link.label) + "</a>";
      })
      .join("");
  }

  function renderPaperCard(publication) {
    var hasVisual = Boolean(publication.visual);
    var authorsMarkup = publication.authors_html || escapeHtml(publication.authors || "");
    var summaryMarkup = publication.summary_html || "";
    var detailCopy = summaryMarkup ? "<p>" + summaryMarkup + "</p>" : "";
    var linksMarkup = renderLinks(publication.links);

    if (linksMarkup) {
      detailCopy += '<div class="link-row">' + linksMarkup + "</div>";
    }

    var metaLine = [
      publication.year ? "<span>" + escapeHtml(publication.year) + "</span>" : "",
      publication.venue ? "<span>" + escapeHtml(publication.venue) + "</span>" : "",
      renderTags(publication.tags),
    ].join("");

    return [
      '<article class="paper-card ' + (hasVisual ? "with-visual" : "text-only") + '" tabindex="0" aria-expanded="false">',
      '  <div class="paper-copy">',
      "    <h3>" + escapeHtml(publication.title) + "</h3>",
      '    <p class="authors">' + authorsMarkup + "</p>",
      '    <div class="meta-line">' + metaLine + "</div>",
      '    <div class="paper-details">' + detailCopy + "</div>",
      "  </div>",
      hasVisual
        ? '  <img src="' + escapeHtml(publication.visual) + '" alt="' + escapeHtml(publication.visual_alt || publication.title) + '">'
        : "",
      '  <button class="paper-toggle" type="button" aria-label="Expand paper">',
      '    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5H7Z"/></svg>',
      "  </button>",
      "</article>",
    ].join("");
  }

  function updateDashboardStats(data) {
    var publicationCount = document.getElementById("publication-count");
    var citationCount = document.getElementById("citation-count");
    var sourceLine = document.getElementById("scholar-source-line");
    if (publicationCount) {
      publicationCount.dataset.target = String(data.source.publications || 0);
      publicationCount.textContent = String(data.source.publications || 0);
    }
    if (citationCount) {
      citationCount.dataset.target = String(data.source.citations || 0);
      citationCount.textContent = String(data.source.citations || 0);
    }
    if (sourceLine) {
      sourceLine.innerHTML =
        '<a href="' +
        escapeHtml(data.source.url) +
        '">' +
        escapeHtml(data.source.label) +
        "</a> · " +
        escapeHtml(data.generated_at_label) +
        ".";
    }
  }

  function updateFeaturedPaper(data) {
    var featured = null;
    var featuredSlug = data.featured_slug;
    (data.publications || []).some(function (publication) {
      if (publication.slug === featuredSlug) {
        featured = publication;
        return true;
      }
      return false;
    });
    if (!featured && data.publications && data.publications.length) {
      featured = data.publications[0];
    }
    if (!featured) return;

    var titleNode = document.getElementById("featured-paper-title");
    var metaNode = document.getElementById("featured-paper-meta");
    var linkNode = document.getElementById("featured-paper-link");

    if (titleNode) titleNode.textContent = featured.title;
    if (metaNode) metaNode.textContent = [featured.venue, featured.year].filter(Boolean).join(" · ");
    if (linkNode) {
      var primaryLink = (featured.links || [])[0];
      if (primaryLink) {
        linkNode.href = primaryLink.href;
        linkNode.textContent = primaryLink.label === "Scholar" ? "View Scholar Entry" : "Read " + primaryLink.label;
      }
    }
  }

  function renderPublicationInterface(data) {
    var tabsRoot = document.getElementById("publication-catalog-tabs");
    var boardRoot = document.getElementById("publication-board");
    if (!tabsRoot || !boardRoot) return;

    var categoryOrder = ["all"].concat(data.category_order || []);
    var labels = data.category_labels || {};
    var counts = data.counts || {};

    tabsRoot.innerHTML = categoryOrder
      .map(function (category, index) {
        var label = labels[category] || category;
        var isActive = index === 0;
        var panelId = category === "all" ? "publication-board" : "pub-panel-" + category;
        return (
          '<button class="catalog-tab' +
          (isActive ? " is-active" : "") +
          '" id="pub-tab-' +
          escapeHtml(category) +
          '" type="button" role="tab" data-pub-tab="' +
          escapeHtml(category) +
          '" aria-selected="' +
          (isActive ? "true" : "false") +
          '" aria-controls="' +
          escapeHtml(panelId) +
          '"' +
          (isActive ? "" : ' tabindex="-1"') +
          ">" +
          escapeHtml(label) +
          ' <span class="catalog-count">' +
          escapeHtml(counts[category] || 0) +
          "</span></button>"
        );
      })
      .join("");

    boardRoot.innerHTML = (data.category_order || [])
      .map(function (category) {
        var label = labels[category] || category;
        var groupTitle = label;
        if (category === "journal") groupTitle = "Journal Articles";
        if (category === "conference") groupTitle = "Conference Proceedings";
        var publications = (data.publications || []).filter(function (publication) {
          return publication.category === category;
        });
        var listClass = category === "journal" ? "paper-list" : "paper-list compact";
        return [
          '<section class="publication-group" id="pub-panel-' + escapeHtml(category) + '" role="tabpanel" data-pub-panel="' + escapeHtml(category) + '" aria-labelledby="pub-tab-' + escapeHtml(category) + '">',
          '  <h3 class="group-title">' + escapeHtml(groupTitle) + "</h3>",
          '  <div class="' + listClass + '">',
          publications.map(renderPaperCard).join(""),
          "  </div>",
          "</section>",
        ].join("");
      })
      .join("");
  }

  function bindPrimaryTabs() {
    document.querySelectorAll(".tab-button[data-tab]").forEach(function (button) {
      button.addEventListener("click", function () {
        activateTab(button.dataset.tab);
      });
    });
  }

  function bindPublicationTabs() {
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

  function bindPaperCards() {
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
  }

  async function hydratePublications() {
    try {
      var response = await fetch("data/publications.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load publications.json");
      var data = await response.json();
      if (!data || !Array.isArray(data.publications)) throw new Error("Invalid publication payload");
      updateDashboardStats(data);
      updateFeaturedPaper(data);
      renderPublicationInterface(data);
      return true;
    } catch (error) {
      console.warn("Publication data fallback engaged.", error);
      return false;
    }
  }

  async function main() {
    await hydratePublications();

    bindPrimaryTabs();
    bindPublicationTabs();
    bindPaperCards();

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
  }

  main();
})();
