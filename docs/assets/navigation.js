(() => {
  const navigation = document.querySelector(".layout > aside nav");
  if (!navigation) return;

  const docsRoot = new URL("../", document.currentScript.src);
  const local = (path) => new URL(path, docsRoot).href;
  const currentPath = new URL(window.location.href).pathname.replace(/\/$/, "");
  const groups = [
    ["Руководство", [["Быстрый старт", "guide/quick-start.html"], ["Установка и обновление", "guide/install.html"], ["Переименование", "guide/rename.html"], ["Конвертация", "guide/conversion.html"], ["Объединение и сжатие", "guide/optimize.html"]]],
    ["Помощь", [["Настройки", "reference/settings.html"], ["Проблемы и решения", "reference/troubleshooting.html"], ["Сообщить об ошибке", "https://github.com/VseMirka200/multifora/issues/new/choose"]]],
    ["Проект", [["Участие в разработке", "https://github.com/VseMirka200/multifora/blob/main/CONTRIBUTING.md"], ["Кодекс поведения", "https://github.com/VseMirka200/multifora/blob/main/CODE_OF_CONDUCT.md"], ["Безопасность", "https://github.com/VseMirka200/multifora/blob/main/SECURITY.md"], ["Поддержка", "https://github.com/VseMirka200/multifora/blob/main/SUPPORT.md"]]],
  ];
  const link = ([label, path]) => {
    const href = path.startsWith("http") ? path : local(path);
    const active = new URL(href).pathname.replace(/\/$/, "") === currentPath;
    return `<a${active ? ' class="active" aria-current="page"' : ""} href="${href}">${label}</a>`;
  };

  navigation.className = "site-nav";
  navigation.setAttribute("aria-label", "Навигация по документации");
  navigation.innerHTML = `<a href="${local("index.html")}">Начало</a><a href="https://github.com/VseMirka200/multifora/releases/latest">Скачать</a>${groups.map(([label, links]) => `<details class="nav-group" open><summary>${label}</summary><div class="nav-group-links">${links.map(link).join("")}</div></details>`).join("")}`;
})();
