(() => {
  const navigation = document.querySelector(".layout > aside nav");
  if (!navigation) return;

  const docsRoot = new URL("../", document.currentScript.src);
  const local = (path) => new URL(path, docsRoot).href;
  const currentPath = new URL(window.location.href).pathname.replace(/\/$/, "");
  const groups = [
    ["Руководство", [["Обзор руководства", "guide/index.html"], ["Быстрый старт", "guide/quick-start.html"], ["Установка и обновление", "guide/install.html"], ["Переименование", "guide/rename.html"], ["Конвертация", "guide/conversion.html"], ["Объединение и сжатие", "guide/optimize.html"]]],
    ["Помощь", [["Настройки", "reference/settings.html"], ["Проблемы и решения", "reference/troubleshooting.html"], ["Связаться с нами", "reference/contact.html"]]],
    ["Проект", [["Проект на GitHub", "https://github.com/VseMirka200/multifora"], ["Участие в разработке", "https://github.com/VseMirka200/multifora/blob/main/docs/CONTRIBUTING.md"], ["Кодекс поведения", "https://github.com/VseMirka200/multifora/blob/main/docs/CODE_OF_CONDUCT.md"], ["Безопасность", "https://github.com/VseMirka200/multifora/blob/main/docs/SECURITY.md"], ["Поддержка", "https://github.com/VseMirka200/multifora/blob/main/docs/SUPPORT.md"], ["Журнал изменений", "https://github.com/VseMirka200/multifora/blob/main/docs/CHANGELOG.md"], ["Поддержать проект", "reference/support-project.html"]]],
  ];
  const link = ([label, path]) => {
    const href = /^(?:https?:|mailto:)/i.test(path) ? path : local(path);
    const url = new URL(href);
    const active = !url.hash && url.protocol !== "mailto:" && url.pathname.replace(/\/$/, "") === currentPath;
    return `<a${active ? ' class="active" aria-current="page"' : ""} href="${href}">${label}</a>`;
  };

  navigation.className = "site-nav";
  navigation.setAttribute("aria-label", "Навигация по документации");
  navigation.innerHTML = `<a href="${local("index.html")}">Начало</a><a href="https://github.com/VseMirka200/multifora/releases/latest">Скачать</a>${groups.map(([label, links]) => `<details class="nav-group" open><summary>${label}</summary><div class="nav-group-links">${links.map(link).join("")}</div></details>`).join("")}`;
})();
