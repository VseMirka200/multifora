(() => {
  const navigation = document.querySelector(".layout > aside nav");
  if (!navigation) return;

  // Относительная база сохраняет работу сайта в подпапке GitHub Pages.
  const docsRoot = new URL("../", document.currentScript.src);
  const local = (path) => new URL(path, docsRoot).href;
  const currentPath = new URL(window.location.href).pathname.replace(/\/$/, "");
  const groups = [
    ["Руководство", [["Обзор руководства", "guide/index.html"], ["Быстрый старт", "guide/quick-start.html"], ["Установка и обновление", "guide/install.html"], ["Переименование", "guide/rename.html"], ["Конвертация", "guide/conversion.html"], ["Объединение и сжатие", "guide/optimize.html"]]],
    ["Помощь", [["Настройки", "reference/settings.html"], ["Проблемы и решения", "reference/troubleshooting.html"], ["Связаться с нами", "reference/contact.html"]]],
    ["Проект", [["Проект на GitHub", "https://github.com/VseMirka200/multifora"], ["Участие в разработке", "https://github.com/VseMirka200/multifora/blob/main/docs/CONTRIBUTING.md"], ["Кодекс поведения", "https://github.com/VseMirka200/multifora/blob/main/docs/CODE_OF_CONDUCT.md"], ["Безопасность", "https://github.com/VseMirka200/multifora/blob/main/docs/SECURITY.md"], ["Поддержка", "https://github.com/VseMirka200/multifora/blob/main/docs/SUPPORT.md"], ["Журнал изменений", "https://github.com/VseMirka200/multifora/blob/main/docs/CHANGELOG.md"], ["Поддержать проект", "reference/support-project.html"]]],
  ];
  // Один список страниц используется меню и поиском на главной странице.
  const link = ([label, path]) => {
    const href = /^(?:https?:|mailto:)/i.test(path) ? path : local(path);
    const url = new URL(href);
    const sameSite = url.origin === window.location.origin;
    const active = sameSite && !url.hash && url.pathname.replace(/\/$/, "") === currentPath;
    return `<a${active ? ' class="active" aria-current="page"' : ""} href="${href}">${label}</a>`;
  };

  navigation.className = "site-nav";
  navigation.setAttribute("aria-label", "Навигация по документации");
  navigation.innerHTML = `${link(["Начало", "index.html"])}<a href="https://github.com/VseMirka200/multifora/releases/latest">Скачать</a>${groups.map(([label, links]) => `<details class="nav-group" open><summary>${label}</summary><div class="nav-group-links">${links.map(link).join("")}</div></details>`).join("")}`;
  const dialog = document.querySelector("#search-dialog");
  if (!dialog) return;

  const input = dialog.querySelector("#search-input");
  const results = dialog.querySelector("#results");
  const pages = groups.flatMap(([, links]) => links);
  function render() {
    const query = input.value.trim().toLocaleLowerCase("ru");
    const matches = pages.filter(([name]) => name.toLocaleLowerCase("ru").includes(query));
    results.innerHTML = matches.length ? matches.map(link).join("") : "<span>Ничего не найдено.</span>";
  }
  function openSearch() {
    render();
    if (!dialog.open) dialog.showModal();
    input.focus();
  }
  document.querySelectorAll("[data-open-search]").forEach((button) => button.addEventListener("click", openSearch));
  dialog.querySelector("[data-close-search]").addEventListener("click", () => dialog.close());
  input.addEventListener("input", render);
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearch();
    }
  });
})();
