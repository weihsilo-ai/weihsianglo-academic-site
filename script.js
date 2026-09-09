(function () {
  document.documentElement.classList.add("motion-ready");
  var THEME_STORAGE_KEY = "site-theme";

  function applyTheme(theme, persist) {
    var isLight = theme === "light";
    document.documentElement.dataset.theme = isLight ? "light" : "dark";

    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      var label = isLight ? "Turn off lights" : "Turn on lights";
      button.setAttribute("aria-label", label);
      button.setAttribute("aria-pressed", String(isLight));
      button.setAttribute("title", label);
      if (button.hasAttribute("data-tooltip")) button.setAttribute("data-tooltip", label);
    });

    if (persist) {
      try {
        localStorage.setItem(THEME_STORAGE_KEY, isLight ? "light" : "dark");
      } catch (error) {}
    }
  }

  function bindThemeToggles() {
    applyTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark", false);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        applyTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light", true);
      });
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderFeaturedAuthors(publication) {
    return escapeHtml(publication.authors || "").replace(/\bWH Lo\b/g, "<strong>WH Lo</strong>");
  }

  function newestFirst(items) {
    return (items || [])
      .map(function (item, index) {
        return { item: item, index: index };
      })
      .sort(function (left, right) {
        return (Number(right.item.year) || 0) - (Number(left.item.year) || 0) || left.index - right.index;
      })
      .map(function (entry) {
        return entry.item;
      });
  }

  function revealPanel(panel) {
    if (!panel) return;

    var items = panel.querySelectorAll(
      ".dashboard-card, .timeline article, .presentation-card, .paper-card, .award-tile"
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

  function renderLinks(links) {
    return (links || [])
      .map(function (link) {
        if (!link || !link.label || !link.href) return "";
        return '<a href="' + escapeHtml(link.href) + '">' + escapeHtml(link.label) + "</a>";
      })
      .join("");
  }

  function publicationLabel(category, index) {
    var prefixes = { journal: "J", conference: "C", preprint: "P", report: "T" };
    return "[" + (prefixes[category] || String(category || "P").charAt(0).toUpperCase()) + (index + 1) + "]";
  }

  function visiblePublicationLinks(publication) {
    return (publication.links || []).filter(function (link) {
      var label = String(link.label || "").toLowerCase();
      if (label === "cv") return false;
      return publication.category !== "journal" || label === "doi";
    });
  }

  function renderPaperCard(publication, label) {
    var hasVisual = Boolean(publication.visual);
    var authorsMarkup = publication.authors_html || escapeHtml(publication.authors || "");
    var summaryMarkup = publication.summary_html || "";
    var detailCopy = summaryMarkup ? "<p>" + summaryMarkup + "</p>" : "";
    var linksMarkup = renderLinks(visiblePublicationLinks(publication));

    var metaLine = [
      publication.year ? "<span>" + escapeHtml(publication.year) + "</span>" : "",
      publication.venue ? '<strong class="publication-venue">' + escapeHtml(publication.venue) + "</strong>" : "",
      linksMarkup ? '<div class="paper-actions">' + linksMarkup + "</div>" : "",
    ].join("");

    return [
      '<article class="paper-card record-card ' + (hasVisual ? "with-visual" : "text-only") + '" tabindex="0" aria-expanded="false" data-publication-label="' + escapeHtml(label) + '">',
      '  <div class="paper-copy">',
      '    <h3><span class="publication-label">' + escapeHtml(label) + "</span><span>" + escapeHtml(publication.title) + "</span></h3>",
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

  function updateScholarMetrics(data) {
    var source = data.source || {};
    var metrics = source.metrics || {};
    var citations = metrics.citations || {};
    var hIndex = metrics.h_index || {};
    var i10Index = metrics.i10_index || {};
    var values = {
      "scholar-citations-all": citations.all == null ? source.citations || 0 : citations.all,
      "scholar-citations-since": citations.since == null ? source.citations || 0 : citations.since,
      "scholar-h-index-all": hIndex.all || 0,
      "scholar-h-index-since": hIndex.since || 0,
      "scholar-i10-index-all": i10Index.all || 0,
      "scholar-i10-index-since": i10Index.since || 0,
    };
    Object.keys(values).forEach(function (id) {
      var node = document.getElementById(id);
      if (node) node.textContent = String(values[id]);
    });

    var sinceLabel = document.getElementById("scholar-since-label");
    if (sinceLabel) sinceLabel.textContent = metrics.since_label || "Since recent";

    var profileLink = document.getElementById("scholar-profile-link");
    if (profileLink && source.url) profileLink.href = source.url;

    var sourceLink = document.getElementById("scholar-source-link");
    if (sourceLink && source.url) sourceLink.href = source.url;

    var updatedLabel = document.getElementById("scholar-updated-label");
    if (updatedLabel) {
      updatedLabel.textContent = source.last_successful_sync_label || data.generated_at_label || "Unknown";
    }

    var barsNode = document.getElementById("scholar-year-bars");
    var chart = barsNode && barsNode.closest(".scholar-chart");
    var points = Array.isArray(metrics.citations_per_year) ? metrics.citations_per_year : [];
    if (!barsNode || !chart || !points.length) return;

    var largest = points.reduce(function (maximum, point) {
      return Math.max(maximum, Number(point.citations) || 0);
    }, 0);
    var axisMax = Math.max(5, Math.ceil(largest / 5) * 5);
    var axis = chart.querySelector(".scholar-axis");
    if (axis) axis.innerHTML = "<span>" + axisMax + "</span><span>" + Math.floor(axisMax / 2) + "</span><span>0</span>";
    barsNode.innerHTML = points
      .map(function (point) {
        var year = Number(point.year) || 0;
        var count = Number(point.citations) || 0;
        var height = Math.round((count / axisMax) * 10000) / 100;
        return (
          '<div class="scholar-year" role="listitem" data-year="' + year + '" data-citations="' + count +
          '" tabindex="0" aria-label="' + year + ": " + count + ' citations" style="--bar-height: ' + height + '%">' +
          '<span class="scholar-bar" aria-hidden="true"></span>' +
          '<span class="scholar-year-label">' + year + "</span></div>"
        );
      })
      .join("");
  }

  function featuredPublications(data) {
    var publications = data.publications || [];
    var requestedSlugs = data.featured_slugs || [data.featured_slug];
    var selected = [];

    requestedSlugs.forEach(function (slug) {
      var publication = publications.find(function (item) {
        return item.slug === slug;
      });
      if (publication && selected.indexOf(publication) === -1) selected.push(publication);
    });
    publications.some(function (publication) {
      if (selected.length >= 3) return true;
      if (selected.indexOf(publication) === -1) selected.push(publication);
      return false;
    });
    return newestFirst(selected.slice(0, 3));
  }

  function renderFeaturedLinks(publication) {
    var doiLink = (publication.links || []).find(function (link) {
      return String(link.label || "").toLowerCase() === "doi" && link.href;
    });
    var links = [];
    if (doiLink) links.push('<a href="' + escapeHtml(doiLink.href) + '">DOI</a>');
    if (!links.length) links.push('<a href="#research">View Publications</a>');
    return '<div class="featured-links">' + links.join("") + "</div>";
  }

  function renderFeaturedPapers(data) {
    var root = document.getElementById("featured-papers-grid");
    if (!root) return;
    root.innerHTML = featuredPublications(data)
      .map(function (publication) {
        var scholarUrl = publication.scholar_url || "#research";
        var authorsMarkup = renderFeaturedAuthors(publication);
        var meta = publication.venue_line || [publication.venue, publication.year].filter(Boolean).join(" · ");
        var categoryPublications = newestFirst((data.publications || []).filter(function (item) {
          return item.category === publication.category;
        }));
        var label = publicationLabel(publication.category, categoryPublications.indexOf(publication));
        return [
          '<article class="dashboard-card featured-card record-card" role="listitem" data-featured-slug="' + escapeHtml(publication.slug) + '">',
          '  <h3><span class="publication-label">' + escapeHtml(label) + '</span><a class="featured-title-link" href="' + escapeHtml(scholarUrl) + '">' + escapeHtml(publication.title) + "</a></h3>",
          '  <p class="featured-authors">' + authorsMarkup + "</p>",
          '  <div class="featured-meta-row">',
          '    <p class="paper-compact-meta">' + escapeHtml(meta) + "</p>",
          "    " + renderFeaturedLinks(publication),
          "  </div>",
          "</article>",
        ].join("");
      })
      .join("");
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
        var categoryPublications = (data.publications || []).filter(function (publication) {
          return publication.category === category;
        });
        var publications = newestFirst(categoryPublications);
        var listClass = category === "journal" ? "paper-list" : "paper-list compact";
        return [
          '<section class="publication-group" id="pub-panel-' + escapeHtml(category) + '" role="tabpanel" data-pub-panel="' + escapeHtml(category) + '" aria-labelledby="pub-tab-' + escapeHtml(category) + '">',
          '  <h3 class="group-title">' + escapeHtml(groupTitle) + "</h3>",
          '  <div class="' + listClass + '">',
          publications
            .map(function (publication, index) {
              return renderPaperCard(publication, publicationLabel(category, index));
            })
            .join(""),
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

  function openLinksInNewTabs() {
    document.querySelectorAll('a[href]:not([href^="#"]):not([href^="mailto:"])').forEach(function (link) {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
    });
  }

  async function hydratePublications() {
    try {
      var response = await fetch("data/publications.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load publications.json");
      var data = await response.json();
      if (!data || !Array.isArray(data.publications)) throw new Error("Invalid publication payload");
      updateScholarMetrics(data);
      renderFeaturedPapers(data);
      renderPublicationInterface(data);
      return true;
    } catch (error) {
      console.warn("Publication data fallback engaged.", error);
      return false;
    }
  }

  async function main() {
    bindThemeToggles();
    await hydratePublications();
    openLinksInNewTabs();

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
