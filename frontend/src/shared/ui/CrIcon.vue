<script setup>
/**
 * Set de iconos de CRONOS — trazos Lucide (1.75px), 20px por defecto.
 * SVG inline (Principio: sin emoji como iconos, sin CDN — la CSP no lo permitiría).
 */
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
})

// path(s) de cada icono (viewBox 0 0 24 24)
const P = {
  search: ['<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'],
  plus: ['<path d="M12 5v14M5 12h14"/>'],
  'chevron-down': ['<path d="m6 9 6 6 6-6"/>'],
  'chevron-right': ['<path d="m9 6 6 6-6 6"/>'],
  'chevron-left': ['<path d="m15 6-6 6 6 6"/>'],
  x: ['<path d="M18 6 6 18M6 6l12 12"/>'],
  check: ['<path d="M20 6 9 17l-5-5"/>'],
  'more-vertical': ['<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>'],
  'alert-triangle': ['<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>'],
  'circle-check': ['<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>'],
  info: ['<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'],
  edit: ['<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'],
  archive: ['<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4"/>'],
  send: ['<path d="M22 2 11 13M22 2l-7 20-4-9-9-4Z"/>'],
  'package-check': ['<path d="m16 16 2 2 4-4"/><path d="M21 10V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l2-1.1"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>'],
  ban: ['<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>'],
  users: ['<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>'],
  building: ['<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M9 6h.01M15 6h.01M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/>'],
  truck: ['<path d="M14 18V6a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h1"/><path d="M14 9h4l3 3v5a1 1 0 0 1-1 1h-1"/><circle cx="7.5" cy="18.5" r="1.5"/><circle cx="17.5" cy="18.5" r="1.5"/>'],
  star: ['<path d="M12 2 15 9l7 .6-5.3 4.6L18.5 21 12 17.3 5.5 21l1.8-6.8L2 9.6 9 9Z"/>'],
  inbox: ['<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.5 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.5A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.5Z"/>'],
  'refresh-cw': ['<path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/>'],
  filter: ['<path d="M22 3H2l8 9.5V19l4 2v-8.5L22 3Z"/>'],
  'log-out': ['<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>'],
  clock: ['<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>'],
  watch: ['<circle cx="12" cy="12" r="6"/><path d="M12 9v3l1.5 1.5M9 2.5 8.5 6M15 2.5l.5 3.5M9 21.5l-.5-3.5M15 21.5l.5-3.5"/>'],
  image: ['<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-4.35-4.35a2 2 0 0 0-2.83 0L4 20"/>'],
  camera: ['<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/><circle cx="12" cy="13" r="3"/>'],
  layers: ['<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>'],
  boxes: ['<path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 1.03 1.75l3 1.65a2 2 0 0 0 1.94 0L10 21v-4l-5-2.72M7 3.34 4 5v4l3 1.72M17 3.34 20 5v4l-3 1.72M14 21l3.03-1.73A2 2 0 0 0 18 17.5v-3.24a2 2 0 0 0-1.03-1.75L14 11M12 8 9 6.5 12 5l3 1.5L12 8Zm0 0v3"/>'],
  history: ['<path d="M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5"/><path d="M12 7v5l3 2"/>'],
  tag: ['<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.8 8.8a2 2 0 0 0 2.8 0l6.4-6.4a2 2 0 0 0 0-2.8Z"/><circle cx="7.5" cy="7.5" r="1"/>'],
  'alert-circle': ['<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>'],
  lock: ['<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'],
  'trending-up': ['<path d="M22 7 13.5 15.5l-5-5L2 17"/><path d="M16 7h6v6"/>'],
  'trending-down': ['<path d="M22 17 13.5 8.5l-5 5L2 7"/><path d="M16 17h6v-6"/>'],
  minus: ['<path d="M5 12h14"/>'],
  'file-text': ['<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5Z"/><path d="M14 2v6h6M8 13h8M8 17h8M8 9h2"/>'],
  'arrow-left': ['<path d="M19 12H5M12 19l-7-7 7-7"/>'],
}

function paths(name) {
  return (P[name] || P.info)[0]
}
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="paths(name)"
  />
</template>
