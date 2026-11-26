(() => {
const key = 'football-language';
const readLanguage = () => {
  const requested = new URL(location.href).searchParams.get('lang');
  if (requested === 'en' || requested === 'ar') return requested;
  try {
    const saved = sessionStorage.getItem(key) || localStorage.getItem(key);
    if (saved === 'en' || saved === 'ar') return saved;
  } catch {}
  return 'en';
};
window.gameLanguage = readLanguage();
try { sessionStorage.setItem(key, window.gameLanguage); } catch {}
const labels = window.arabicLabels || {};

window.arabic = gameLanguage === 'ar';
window.withGameLanguage = (address, language = gameLanguage) => {
  const url = new URL(address, location.href);
  if (url.origin === location.origin) url.searchParams.set('lang', language);
  return url.href;
};
window.tr = (text, ...values) => {
  if (arabic && !values.length && !labels[text] && /[0-9]/.test(text)) {
    const numbers = [];
    const pattern = text.replace(/[0-9]+/g, number => {
      if (text.startsWith('You joined as') && numbers.length === 1) return number;
      numbers.push(number);
      return '{' + (numbers.length - 1) + '}';
    });
    if (labels[pattern]) return tr(pattern, ...numbers);
  }
  const template = arabic ? (labels[text] || text) : text;
  return template.replace(/\{(\d+)\}/g, (match, index) => values[index] ?? match);
};
document.documentElement.lang = gameLanguage;
document.documentElement.dir = arabic ? 'rtl' : 'ltr';
document.addEventListener('DOMContentLoaded', () => {
  if (arabic) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.parentElement.closest('script, style, [data-team-name]') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const original = node.data.trim();
      if (original) node.data = node.data.replace(original, tr(original));
    }
    for (const node of document.querySelectorAll('[aria-label], [alt], [placeholder]')) {
      for (const attribute of ['aria-label', 'alt', 'placeholder']) {
        if (node.hasAttribute(attribute)) node.setAttribute(attribute, tr(node.getAttribute(attribute)));
      }
    }
    for (const link of document.querySelectorAll('.site-nav')) link.textContent = tr('The Football IQ Game');
    document.title = tr(document.title) !== document.title ? tr(document.title) : document.title.split(' | ').map(title => tr(title)).join(' | ');
  }
  for (const link of document.querySelectorAll('a[href]')) {
    if (!link.getAttribute('href').startsWith('#')) link.href = withGameLanguage(link.href);
  }
  for (const form of document.querySelectorAll('form[method="post"]')) {
    const destination = form.getAttribute('action') || location.href;
    form.setAttribute('action', withGameLanguage(destination));
  }
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'language-switch';
  button.textContent = arabic ? 'English' : 'العربية';
  button.lang = arabic ? 'en' : 'ar';
  button.addEventListener('click', () => {
    const language = arabic ? 'en' : 'ar';
    try {
      sessionStorage.setItem(key, language);
      localStorage.setItem(key, language);
    } catch {}
    location.replace(withGameLanguage(location.href, language));
  });
  document.body.prepend(button);
});

})();
