/**
 * Texture — the procedural macro-texture registry (zero copyright):
 * dawn-limb, amber-crust, amber-planet, teal-planet, red-planet, ink-planet,
 * batik, gold-dust, ember-field, blueprint, cream-leaf, paper-print.
 *
 * All fields are seeded feTurbulence compositions; internal drift is
 * frame-driven. Add new textures in ../textures/ and register below.
 */
export { textures, type TextureId } from '../textures';
export { Backdrop as TextureCanvas, W, H } from '../textures/kit';
export { mulberry32 } from 'claude-motion-core';
