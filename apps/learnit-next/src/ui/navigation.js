function element(tag, attributes = {}, children = []) {
  const value = document.createElement(tag);
  for (const [name, item] of Object.entries(attributes)) {
    if (name === 'className') value.className = item;
    else if (name === 'text') value.textContent = item;
    else if (name === 'disabled') value.disabled = Boolean(item);
    else if (name.startsWith('on') && typeof item === 'function') value.addEventListener(name.slice(2).toLowerCase(), item);
    else if (item !== undefined && item !== null) value.setAttribute(name, String(item));
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child == null) continue;
    value.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return value;
}

export function createNavigationDrawer(root, onNavigate) {
  if (!root || typeof onNavigate !== 'function') {
    throw new TypeError('Navigation drawer requires root and onNavigate');
  }

  const drawerId = 'learnit-navigation-drawer';
  const trigger = element('button', {
    type: 'button',
    className: 'nav-menu-trigger',
    text: 'Menu',
    'aria-expanded': 'false',
    'aria-controls': drawerId,
  });
  const closeButton = element('button', {
    type: 'button',
    className: 'nav-drawer-close',
    text: 'Fermer',
    'aria-label': 'Fermer la navigation',
  });
  const todayButton = element('button', {
    type: 'button',
    className: 'nav-drawer-link',
    text: 'Aujourd’hui',
    'data-shell-view': 'today',
    disabled: true,
  });
  const libraryButton = element('button', {
    type: 'button',
    className: 'nav-drawer-link',
    text: 'Tous les cours',
    'data-shell-view': 'library',
  });
  const importButton = element('button', {
    type: 'button',
    className: 'nav-drawer-link nav-drawer-link-secondary',
    text: 'Importer un cours',
    'data-shell-view': 'import',
  });
  const drawer = element('aside', {
    id: drawerId,
    className: 'nav-drawer',
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'learnit-navigation-title',
    hidden: 'hidden',
  }, [
    element('div', {className: 'nav-drawer-header'}, [
      element('strong', {id: 'learnit-navigation-title', text: 'Learn-it'}),
      closeButton,
    ]),
    element('nav', {'aria-label': 'Navigation principale'}, [
      todayButton,
      element('div', {className: 'nav-drawer-group'}, [
        element('span', {className: 'nav-drawer-group-title', text: 'Bibliothèque'}),
        libraryButton,
        importButton,
      ]),
    ]),
  ]);
  const backdrop = element('div', {
    className: 'nav-drawer-backdrop',
    hidden: 'hidden',
    'aria-hidden': 'true',
  });

  let previouslyFocused = null;
  const previousInert = new Map();

  function backgroundElements() {
    return [...root.children].filter(child => child !== drawer && child !== backdrop);
  }

  function applyBackgroundInert(active) {
    if (active) {
      previousInert.clear();
      for (const child of backgroundElements()) {
        previousInert.set(child, child.hasAttribute('inert'));
        child.setAttribute('inert', '');
      }
      return;
    }
    for (const [child, wasInert] of previousInert) {
      if (!child.isConnected) continue;
      if (!wasInert) child.removeAttribute('inert');
    }
    previousInert.clear();
  }

  function focusables() {
    return [...drawer.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])')]
      .filter(item => !item.hasAttribute('hidden'));
  }

  function open() {
    if (!drawer.hidden) return;
    previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : trigger;
    drawer.hidden = false;
    backdrop.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    document.body.classList.add('nav-drawer-open');
    applyBackgroundInert(true);
    queueMicrotask(() => closeButton.focus());
  }

  function close({restoreFocus = true} = {}) {
    if (drawer.hidden) return;
    drawer.hidden = true;
    backdrop.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-drawer-open');
    applyBackgroundInert(false);
    if (restoreFocus) {
      queueMicrotask(() => (previouslyFocused?.isConnected ? previouslyFocused : trigger).focus());
    }
  }

  trigger.addEventListener('click', open);
  closeButton.addEventListener('click', () => close());
  backdrop.addEventListener('click', () => close());

  drawer.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    const items = focusables();
    if (!items.length) return;
    const first = items[0];
    const last = items.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  for (const button of [todayButton, libraryButton, importButton]) {
    button.addEventListener('click', () => {
      const view = button.getAttribute('data-shell-view');
      close({restoreFocus: false});
      onNavigate(view);
    });
  }

  function setTodayAvailable(available) {
    todayButton.disabled = !available;
    todayButton.setAttribute('aria-disabled', String(!available));
  }

  function setActiveView(view) {
    for (const button of [todayButton, libraryButton, importButton]) {
      const active = button.getAttribute('data-shell-view') === view
        || (view === 'library' && button.getAttribute('data-shell-view') === 'import');
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    }
  }

  return Object.freeze({
    trigger,
    drawer,
    backdrop,
    open,
    close,
    setTodayAvailable,
    setActiveView,
  });
}
