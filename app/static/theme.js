(() => {
  const STORAGE_KEY = "color-scheme";
  const DARK_QUERY = window.matchMedia("(prefers-color-scheme: dark)");

  function getMeta() {
    let meta = document.querySelector('meta[name="color-scheme"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "color-scheme";
      meta.content = "light dark";
      document.head.appendChild(meta);
    }
    return meta;
  }

  function getStoredScheme() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch {
      return null;
    }
  }

  function getSystemScheme() {
    return DARK_QUERY.matches ? "dark" : "light";
  }

  function getEffectiveScheme() {
    const metaContent = getMeta().content;
    if (metaContent === "light" || metaContent === "dark") {
      return metaContent;
    }
    return getStoredScheme() ?? getSystemScheme();
  }

  function syncToggleControls(effective) {
    const isDark = effective === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((el) => {
      if (el instanceof HTMLInputElement && el.type === "checkbox") {
        el.checked = isDark;
        el.setAttribute("aria-checked", String(isDark));
      } else {
        el.setAttribute("aria-pressed", String(isDark));
      }
    });
  }

  function applyScheme(stored) {
    const content = stored === "light" || stored === "dark" ? stored : "light dark";
    const effective = stored ?? getSystemScheme();
    getMeta().content = content;
    document.documentElement.dataset.theme = effective;
    syncToggleControls(effective);
    window.dispatchEvent(
      new CustomEvent("wrapper:themechange", {
        detail: { stored, effective },
      })
    );
  }

  function setTargetScheme(target) {
    const system = getSystemScheme();
    let nextStored = null;
    if (target !== system) {
      nextStored = target;
      try {
        localStorage.setItem(STORAGE_KEY, target);
      } catch {
        // Apply to current page even if storage is unavailable
      }
    } else {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // Ignore storage errors
      }
    }
    applyScheme(nextStored);
  }

  function toggleScheme() {
    const current = getEffectiveScheme();
    setTargetScheme(current === "dark" ? "light" : "dark");
  }

  function bindToggles() {
    document.querySelectorAll("[data-theme-toggle]").forEach((el) => {
      if (el.dataset.themeBound === "true") return;
      el.dataset.themeBound = "true";
      if (el instanceof HTMLInputElement && el.type === "checkbox") {
        el.addEventListener("change", () => {
          setTargetScheme(el.checked ? "dark" : "light");
        });
      } else {
        el.addEventListener("click", toggleScheme);
      }
    });
    syncToggleControls(getEffectiveScheme());
  }

  // Keep open tabs/apps synchronized when theme changes elsewhere
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY || event.key === null) {
      applyScheme(getStoredScheme());
    }
  });

  // Notify JS consumers & sync switch when OS preference changes while following system
  const handleSystemChange = () => {
    if (!getStoredScheme()) {
      const effective = getSystemScheme();
      document.documentElement.dataset.theme = effective;
      syncToggleControls(effective);
      window.dispatchEvent(
        new CustomEvent("wrapper:themechange", {
          detail: { stored: null, effective },
        })
      );
    }
  };
  if (typeof DARK_QUERY.addEventListener === "function") {
    DARK_QUERY.addEventListener("change", handleSystemChange);
  }

  // Sync root dataset immediately
  document.documentElement.dataset.theme = getEffectiveScheme();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindToggles);
  } else {
    bindToggles();
  }

  window.WrapperTheme = {
    getEffectiveScheme,
    getStoredScheme,
    toggleScheme,
  };
})();
