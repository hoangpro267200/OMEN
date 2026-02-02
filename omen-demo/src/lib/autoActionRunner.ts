/**
 * AutoActionRunner — runs demo actions (click, input) with delays.
 * Elements are found by data-demo-target="id" or id="id".
 */

import type { DemoScene, DemoAction } from './demoScenes';

const HIGHLIGHT_CLASS = 'demo-action-highlight';
const HIGHLIGHT_DURATION_MS = 800;

function findElement(target: string): HTMLElement | null {
  const id = target.startsWith('#') ? target.slice(1) : target;
  const byData = document.querySelector(`[data-demo-target="${id}"]`);
  if (byData) return byData as HTMLElement;
  const byId = document.getElementById(id);
  if (byId) return byId;
  const bySelector = document.querySelector(target);
  return bySelector ? (bySelector as HTMLElement) : null;
}

function highlightElement(el: HTMLElement): void {
  el.classList.add(HIGHLIGHT_CLASS);
  document.documentElement.style.setProperty(
    '--demo-highlight',
    '2px solid var(--accent-amber)'
  );
  setTimeout(() => {
    el.classList.remove(HIGHLIGHT_CLASS);
  }, HIGHLIGHT_DURATION_MS);
}

function runAction(action: DemoAction): Promise<void> {
  if (action.type === 'wait') {
    return Promise.resolve();
  }

  const target = action.target ?? '';
  const el = target ? findElement(target) : null;
  if (!el) return Promise.resolve();

  if (action.type === 'highlight') {
    highlightElement(el!);
    return Promise.resolve();
  }

  highlightElement(el!);

  if (action.type === 'click') {
    el!.click();
    return Promise.resolve();
  }

  if (action.type === 'input' && 'value' in action && action.value !== undefined) {
    const input = el as HTMLInputElement | HTMLTextAreaElement;
    input.focus();
    input.value = action.value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return Promise.resolve();
  }

  return Promise.resolve();
}

/**
 * Run all actions for a scene after navigating to its route.
 * Call after navigation; wait for route to render (e.g. 400ms) then run actions with delays.
 */
export async function runSceneActions(
  scene: DemoScene,
  onProgress?: (actionIndex: number) => void
): Promise<void> {
  if (scene.actions.length === 0) return;

  await new Promise((r) => setTimeout(r, 600));

  for (let i = 0; i < scene.actions.length; i++) {
    const action = scene.actions[i];
    onProgress?.(i);
    await new Promise((r) => setTimeout(r, action.delay));
    await runAction(action);
  }
}
