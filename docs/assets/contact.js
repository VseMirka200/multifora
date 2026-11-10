(() => {
  const subject = document.querySelector("#subject");
  const message = document.querySelector("#message");
  const templates = {
    bug: ["Мультифора — сообщение об ошибке", "Здравствуйте!\n\nВерсия Мультифоры:\nВерсия Windows:\n\nЧто я делал(а):\n\nЧто произошло:\n\nКакой результат ожидался:\n\nСпасибо!"],
    idea: ["Мультифора — предложение", "Здравствуйте!\n\nЯ предлагаю улучшить Мультифору:\n\n\nЭто поможет:\n\nСпасибо!"],
    question: ["Мультифора — вопрос", "Здравствуйте!\n\nУ меня есть вопрос о Мультифоре:\n\n\nСпасибо!"],
    other: ["Мультифора — обращение", "Здравствуйте!\n\n\n\nСпасибо!"],
  };
  const address = "vsemirka200@bk.ru";
  const providers = document.querySelectorAll("[data-provider]");
  const openEmail = document.querySelector("#open-email");
  const emailSection = document.querySelector("#email");

  openEmail.addEventListener("click", () => {
    const opening = emailSection.hidden;
    emailSection.hidden = !opening;
    openEmail.setAttribute("aria-expanded", String(opening));
    openEmail.textContent = opening ? "Скрыть форму" : "Написать письмо";
    if (opening) emailSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  function updateLinks() {
    const params = new URLSearchParams({ to: address, subject: subject.value, body: message.value });
    const gmail = new URLSearchParams({ view: "cm", fs: "1", to: address, su: subject.value, body: message.value });
    const links = {
      yandex: `https://mail.yandex.ru/#compose?${params}`,
      mailru: `https://e.mail.ru/compose/?${params}`,
      gmail: `https://mail.google.com/mail/?${gmail}`,
      outlook: `https://outlook.live.com/mail/0/deeplink/compose?${params}`,
      yahoo: `https://compose.mail.yahoo.com/?${params}`,
      proton: `https://mail.proton.me/u/0/compose?${params}`,
    };
    providers.forEach((link) => { link.href = links[link.dataset.provider]; });
  }

  document.querySelectorAll("[data-template]").forEach((button) => {
    button.addEventListener("click", () => {
      [subject.value, message.value] = templates[button.dataset.template];
      document.querySelectorAll("[data-template]").forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      updateLinks();
    });
    button.setAttribute("aria-pressed", String(button.dataset.template === "question"));
  });
  subject.addEventListener("input", updateLinks);
  message.addEventListener("input", updateLinks);
  updateLinks();
})();
